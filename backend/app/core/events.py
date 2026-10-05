"""
Application lifecycle events: startup and shutdown hooks.
"""

import logging
import os

from app.config import get_settings

logger = logging.getLogger(__name__)


async def on_startup() -> None:
    """Execute on application startup."""
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Ensure ChromaDB persist directory exists
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

    logger.info(f"🚀 {settings.APP_NAME} starting in {settings.APP_ENV} mode")
    logger.info(f"📂 Upload directory: {settings.UPLOAD_DIR}")
    logger.info(f"🧠 Gemini model: {settings.GEMINI_MODEL}")
    logger.info(f"📊 Embedding model: {settings.HF_EMBEDDING_MODEL}")

    # Initialize database tables
    try:
        import app.models  # noqa: F401
        from app.db.session import engine
        from app.models.base import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database schema initialized successfully")

        # Seed initial job listings if table is empty
        from app.db.seed_data import seed_jobs_if_empty
        from app.db.session import async_session_factory

        async with async_session_factory() as session:
            await seed_jobs_if_empty(session)
    except Exception as exc:
        logger.warning(f"⚠️ Database schema initialization postponed or skipped: {exc}")

    # Start self-ping keep-alive to prevent Render free tier cold sleep.
    # Render sleeps services after 15 min of inactivity; we ping every 10 min.
    _start_keepalive()


def _start_keepalive() -> None:
    """Launch a background asyncio task that self-pings /health every 10 minutes."""
    import asyncio

    port = int(os.environ.get("PORT", 8000))
    health_url = f"http://localhost:{port}/api/v1/health"

    async def _ping_loop() -> None:
        # Wait 2 minutes after startup before first ping so the server is ready
        await asyncio.sleep(120)
        while True:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(health_url)
                    logger.debug(f"[KeepAlive] Self-ping → {resp.status_code}")
            except Exception as exc:
                logger.debug(f"[KeepAlive] Self-ping failed (non-critical): {exc}")
            # Sleep 10 minutes before next ping
            await asyncio.sleep(10 * 60)

    task = asyncio.create_task(_ping_loop())
    # Store on the event loop so it can be cancelled on shutdown
    _keepalive_tasks.append(task)
    logger.info("🔄 Keep-alive self-ping started (interval: 10 min)")


# Module-level list to hold the keep-alive task reference
_keepalive_tasks: list = []


async def on_shutdown() -> None:
    """Execute on application shutdown."""
    logger.info("🛑 Application shutting down...")

    # Cancel keep-alive tasks
    for task in _keepalive_tasks:
        task.cancel()
    _keepalive_tasks.clear()

    logger.info("✅ Shutdown complete.")
