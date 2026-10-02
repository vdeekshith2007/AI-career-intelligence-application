"""
Resume repository — data access layer for Resume operations.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume
from app.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    """Resume-specific data access methods."""

    def __init__(self, db: AsyncSession):
        super().__init__(Resume, db)

    async def get_by_user(
        self, user_id: UUID, limit: int = 50
    ) -> Sequence[Resume]:
        """Get all resumes for a user, ordered by newest first."""
        result = await self.db.execute(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_hash(
        self, user_id: UUID, file_hash: str
    ) -> Resume | None:
        """Find a resume by file hash (deduplication)."""
        result = await self.db.execute(
            select(Resume).where(
                Resume.user_id == user_id,
                Resume.file_hash == file_hash,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_for_user(self, user_id: UUID) -> Resume | None:
        """Get the most recent resume for a user."""
        result = await self.db.execute(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
