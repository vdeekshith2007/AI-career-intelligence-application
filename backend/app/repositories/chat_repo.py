"""
Chat repository — data access layer for Chat operations.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.repositories.base import BaseRepository


class ChatRepository(BaseRepository[ChatSession]):
    """Chat-specific data access methods."""

    def __init__(self, db: AsyncSession):
        super().__init__(ChatSession, db)

    async def get_user_sessions(
        self, user_id: UUID, limit: int = 50
    ) -> Sequence[ChatSession]:
        """Get all sessions for a user, ordered by most recent."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_session_messages(
        self, session_id: UUID
    ) -> Sequence[ChatMessage]:
        """Get all messages for a session, ordered chronologically."""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        return result.scalars().all()

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        sources: dict | None = None,
        token_count: int | None = None,
    ) -> ChatMessage:
        """Add a message to a chat session."""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            sources=sources,
            token_count=token_count,
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message
