"""
Chat Pydantic schemas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Create a new chat session."""

    title: str | None = Field(None, max_length=255)


class ChatSessionResponse(BaseModel):
    """Chat session response."""

    id: UUID
    title: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    """Send a message to the career advisor."""

    content: str = Field(..., min_length=1, max_length=5000)


class ChatMessageResponse(BaseModel):
    """Chat message response."""

    id: UUID
    role: str
    content: str
    sources: dict[str, Any] | None = None
    token_count: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    """Chat session with full message history."""

    session: ChatSessionResponse
    messages: list[ChatMessageResponse]
