"""
FastAPI application entrypoint.

Configures CORS, middleware, routers, and application lifespan events.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.v1.router import api_v1_router
from app.config import get_settings
from app.core.events import on_shutdown, on_startup
from app.core.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    await on_startup()
    yield
    await on_shutdown()


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered career intelligence platform with resume analysis, job matching, and personalized guidance.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # --- Root endpoint: API gateway info ---
    @app.get("/", include_in_schema=False, tags=["Root"])
    async def root() -> JSONResponse:
        """API root — returns service info and health status."""
        return JSONResponse({
            "service": settings.APP_NAME,
            "version": "1.0.0",
            "status": "online",
            "environment": settings.APP_ENV,
            "api": "/api/v1",
            "health": "/api/v1/health",
            "docs": "/docs",
        })

    # --- Global Unhandled Exception Handler (Prevents stack trace / information leakage) ---
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(f"[{request_id}] Unhandled internal exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred. Please contact support.",
                "request_id": request_id,
            },
        )

    # --- Middleware ---
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers ---
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
