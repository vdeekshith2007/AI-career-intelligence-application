"""
Health check endpoints.
"""

from fastapi import APIRouter, status

from app.config import get_settings

router = APIRouter()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Basic health check (no slash)",
    include_in_schema=False,
)
@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
)
async def health_check():
    """Basic liveness probe."""
    return {
        "status": "healthy",
        "service": get_settings().APP_NAME,
        "version": "0.1.0",
    }


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
)
async def readiness_check():
    """
    Readiness probe — checks connectivity to dependent services.

    Returns 200 if all critical services are reachable, 503 otherwise.
    """
    checks = {
        "database": False,
        "chromadb": False,
    }

    # Check database
    try:
        from sqlalchemy import text

        from app.db.session import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            checks["database"] = True
    except Exception:
        pass

    # Check ChromaDB
    try:
        import httpx

        settings = get_settings()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}/api/v2/heartbeat"
            )
            checks["chromadb"] = resp.status_code == 200
    except Exception:
        pass

    all_healthy = all(checks.values())
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
    }
