"""
Authentication endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.api.v1.schemas.user import UserProfile
from app.config import get_settings
from app.core.exceptions import AlreadyExistsException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.session import get_async_session
from app.models.user import User

router = APIRouter()
settings = get_settings()


@router.post(
    "/register",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new user account."""
    normalized_email = payload.email.lower().strip()

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == normalized_email))
    existing = result.scalar_one_or_none()
    if existing:
        raise AlreadyExistsException("User", "email")

    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT tokens",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Authenticate user and return JWT token pair."""
    normalized_email = payload.email.lower().strip()

    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedException("Invalid email or password.")

    if not user.is_active:
        raise UnauthorizedException("Account is deactivated.")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Issue a new access token using a valid refresh token."""
    decoded = decode_token(payload.refresh_token)

    if decoded.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token.")

    user_id = decoded.get("sub")
    try:
        user_uuid = UUID(str(user_id))
    except (ValueError, TypeError, AttributeError) as err:
        raise UnauthorizedException("Invalid token subject.") from err

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthorizedException("User not found or deactivated.")

    access_token = create_access_token(user.id)
    new_refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (invalidate tokens)",
)
async def logout(
    current_user: User = Depends(get_current_user),
):
    """Logout the current user. Client should discard tokens."""
    # In a production system, you'd blacklist the token in Redis.
    # For now, the client simply discards the token.
    return MessageResponse(message="Logged out successfully.")


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get the authenticated user's profile."""
    return current_user
