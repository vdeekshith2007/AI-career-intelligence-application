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

    # In local development on Windows, resolve WSL2 IP if Docker PostgreSQL is running there
    if ("@localhost:5432" in url or "@127.0.0.1:5432" in url) and os.name == "nt":
        wsl_ip = None
        for cmd in [["wsl", "-d", "Ubuntu", "hostname", "-I"], ["wsl", "hostname", "-I"]]:
            try:
                out = subprocess.check_output(cmd, text=True, timeout=2.0).strip()
                ips = out.split()
                if ips:
                    candidate_ip = ips[0]
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_sock.settimeout(0.5)
                    test_sock.connect((candidate_ip, 5432))
                    test_sock.close()
                    wsl_ip = candidate_ip
                    break
            except Exception:
                continue

        if wsl_ip:
            url = url.replace("@localhost:5432", f"@{wsl_ip}:5432").replace(
                "@127.0.0.1:5432", f"@{wsl_ip}:5432"
            )
        else:
            url = url.replace("@localhost:5432", "@127.0.0.1:5432")
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
