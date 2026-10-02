"""
User profile endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.auth import MessageResponse
from app.api.v1.schemas.user import UpdateProfileRequest, UserProfile
from app.core.security import get_current_user
from app.db.session import get_async_session
from app.models.user import User

router = APIRouter()


@router.get(
    "/profile",
    response_model=UserProfile,
    summary="Get user profile",
)
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the authenticated user's full profile."""
    return current_user


@router.put(
    "/profile",
    response_model=UserProfile,
    summary="Update user profile",
)
async def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update the authenticated user's profile."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.profile_data is not None:
        current_user.profile_data = payload.profile_data

    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)

    return current_user


@router.delete(
    "/account",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete user account",
)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Deactivate the user's account (soft-delete)."""
    current_user.is_active = False
    db.add(current_user)
    await db.flush()

    return MessageResponse(message="Account deactivated successfully.")
