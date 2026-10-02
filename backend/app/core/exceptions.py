"""
Custom exception hierarchy for structured error handling.

All exceptions map to HTTP status codes and produce consistent JSON responses.
"""

from typing import Any

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundException(AppException):
    """Resource not found (404)."""

    def __init__(self, resource: str = "Resource", identifier: Any = None):
        detail = f"{resource} not found."
        if identifier:
            detail = f"{resource} with id '{identifier}' not found."
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class AlreadyExistsException(AppException):
    """Resource already exists (409)."""

    def __init__(self, resource: str = "Resource", field: str = ""):
        detail = f"{resource} already exists."
        if field:
            detail = f"{resource} with this {field} already exists."
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UnauthorizedException(AppException):
    """Authentication required (401)."""

    def __init__(self, detail: str = "Authentication required."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(AppException):
    """Insufficient permissions (403)."""

    def __init__(self, detail: str = "You don't have permission to perform this action."):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ValidationException(AppException):
    """Business logic validation error (422)."""

    def __init__(self, detail: str = "Validation error."):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class FileUploadException(AppException):
    """File upload error (400)."""

    def __init__(self, detail: str = "File upload failed."):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class AIServiceException(AppException):
    """AI/LLM service error (503)."""

    def __init__(self, detail: str = "AI service temporarily unavailable."):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


class RateLimitException(AppException):
    """Rate limit exceeded (429)."""

    def __init__(self, detail: str = "Rate limit exceeded. Please try again later."):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)
