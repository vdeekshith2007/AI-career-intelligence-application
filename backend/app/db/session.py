"""
Async SQLAlchemy session factory.

Provides the async engine, session factory, and a FastAPI dependency
for injecting database sessions into route handlers.
"""

import os
import socket
import subprocess
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()


# --- Normalize DATABASE_URL for asyncpg & WSL environment ---
def _resolve_db_url(url: str) -> str:
    """Normalize the database URL for asyncpg compatibility and WSL2 support."""
    # Render.com provides postgres:// — rewrite to asyncpg-compatible form
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # In local development on Windows, resolve the correct host for PostgreSQL.
    # wslrelay (127.0.0.1:5432) may appear to listen but rejects asyncpg connections —
    # we probe ALL IPs from `wsl hostname -I` plus 127.0.0.1 and pick the first that
    # accepts a TCP connection on port 5432 (using connect_ex to avoid exceptions).
    if ("@localhost:5432" in url or "@127.0.0.1:5432" in url) and os.name == "nt":
        candidates: list[str] = []

        # Collect all WSL IPs (eth0 + docker bridges, etc.)
        for cmd in [["wsl", "-d", "Ubuntu", "hostname", "-I"], ["wsl", "hostname", "-I"]]:
            try:
                out = subprocess.check_output(cmd, text=True, timeout=2.0).strip()
                candidates.extend(ip for ip in out.split() if ip)
                break
            except Exception:
                continue

        # Add 127.0.0.1 as a final fallback candidate
        if "127.0.0.1" not in candidates:
            candidates.append("127.0.0.1")

        resolved_ip: str | None = None
        for ip in candidates:
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.settimeout(1.0)
                result = test_sock.connect_ex((ip, 5432))
                test_sock.close()
                if result == 0:
                    resolved_ip = ip
                    break
            except Exception:
                continue

        # If not resolved, attempt to start the PostgreSQL container in WSL and re-probe
        if not resolved_ip:
            for start_cmd in [
                ["wsl", "-d", "Ubuntu", "-u", "root", "docker", "start", "career-db"],
                ["wsl", "-u", "root", "docker", "start", "career-db"],
            ]:
                try:
                    subprocess.run(
                        start_cmd,
                        timeout=6.0,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    import time
                    time.sleep(1.5)
                    for ip in candidates:
                        try:
                            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            test_sock.settimeout(1.0)
                            result = test_sock.connect_ex((ip, 5432))
                            test_sock.close()
                            if result == 0:
                                resolved_ip = ip
                                break
                        except Exception:
                            continue
                    if resolved_ip:
                        break
                except Exception:
                    continue

        if resolved_ip:
            url = url.replace("@localhost:5432", f"@{resolved_ip}:5432").replace(
                "@127.0.0.1:5432", f"@{resolved_ip}:5432"
            )
            # Keep WSL alive in background so Docker container never idles out
            try:
                subprocess.Popen(
                    ["wsl", "-d", "Ubuntu", "-u", "root", "sleep", "infinity"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass
    return url


_db_url = _resolve_db_url(settings.DATABASE_URL)

# --- Async Engine ---
# Pool settings optimized for Render.com free tier (max ~25 DB connections)
# Production: pool_size=5, max_overflow=5  → max 10 concurrent connections
# Local dev: same settings to stay consistent
engine = create_async_engine(
    _db_url,
    echo=settings.DATABASE_ECHO,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=1800,   # Recycle every 30 min to avoid stale connections
    pool_timeout=30,     # Wait up to 30s for a free connection
    connect_args={
        "server_settings": {"application_name": "ai_career_intelligence"},
    } if "asyncpg" in _db_url else {},
)

# --- Session Factory ---
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    Usage:
        @router.get("/")
        async def endpoint(db: DBSession):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
