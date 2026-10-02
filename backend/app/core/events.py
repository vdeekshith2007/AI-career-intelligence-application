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
    except Exception as exc:
        logger.warning(f"⚠️ Database schema initialization postponed or skipped: {exc}")


async def on_shutdown() -> None:
    """Execute on application shutdown."""
    logger.info("🛑 Application shutting down...")

    # Close database connections, cleanup resources, etc.
    # (Session cleanup is handled by the session factory context manager)

    logger.info("✅ Shutdown complete.")
