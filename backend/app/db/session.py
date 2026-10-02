"""
Async SQLAlchemy session factory.

Provides the async engine, session factory, and a FastAPI dependency
for injecting database sessions into route handlers.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

import os
import socket
import subprocess

# --- Normalize DATABASE_URL for asyncpg & WSL environment ---
def _resolve_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # In local development on Windows, check if localhost:5432 is directly reachable.
    # If not, resolve the WSL2 IP where Docker PostgreSQL is running.
    if ("@localhost:5432" in url or "@127.0.0.1:5432" in url) and os.name == "nt":
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            sock.connect(("127.0.0.1", 5432))
            sock.close()
        except Exception:
            for cmd in [["wsl", "-d", "Ubuntu", "hostname", "-I"], ["wsl", "hostname", "-I"]]:
                try:
                    out = subprocess.check_output(cmd, text=True, timeout=1.5).strip()
                    ips = out.split()
                    if ips:
                        wsl_ip = ips[0]
                        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        test_sock.settimeout(0.5)
                        test_sock.connect((wsl_ip, 5432))
                        test_sock.close()
                        url = url.replace("@localhost:5432", f"@{wsl_ip}:5432").replace("@127.0.0.1:5432", f"@{wsl_ip}:5432")
                        break
                except Exception:
                    continue
    return url

_db_url = _resolve_db_url(settings.DATABASE_URL)

# --- Async Engine ---
engine = create_async_engine(
    _db_url,
    echo=settings.DATABASE_ECHO,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
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
