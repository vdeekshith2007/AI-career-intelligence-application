"""
User Pydantic schemas (request/response models).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserProfile(BaseModel):
    """User profile response."""

    id: UUID
    email: EmailStr
    full_name: str
    avatar_url: str | None = None
    role: str
    profile_data: dict[str, Any] | None = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    """Update user profile request."""

    full_name: str | None = Field(None, min_length=2, max_length=255)
    profile_data: dict[str, Any] | None = None


class UserListItem(BaseModel):
    """Compact user representation for admin lists."""

    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}
