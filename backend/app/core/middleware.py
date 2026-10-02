"""
Custom middleware for request logging, timing, and error handling.
"""

import logging
import time
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing and correlation ID."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate correlation ID for request tracing
        request_id = str(uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.perf_counter()

        # Log incoming request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"FAILED after {duration:.1f}ms — {exc}"
            )
            raise

        duration = (time.perf_counter() - start_time) * 1000

        # Log completed request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"→ {response.status_code} in {duration:.1f}ms"
        )

        # Add headers for debugging
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.1f}ms"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response to mitigate common web vulnerabilities."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

