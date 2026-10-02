"""
Job repository — data access layer for Job operations.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobMatch
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Job-specific data access methods."""

    def __init__(self, db: AsyncSession):
        super().__init__(Job, db)

    async def search(
        self,
        *,
        query: str | None = None,
        location: str | None = None,
        work_type: str | None = None,
        experience_level: str | None = None,
        limit: int = 20,
    ) -> Sequence[Job]:
        """Search active jobs with optional filters."""
        stmt = select(Job).where(Job.is_active == True)

        if query:
            stmt = stmt.where(
                Job.title.ilike(f"%{query}%") | Job.company.ilike(f"%{query}%")
            )
        if location:
            stmt = stmt.where(Job.location.ilike(f"%{location}%"))
        if work_type:
            stmt = stmt.where(Job.work_type == work_type)
        if experience_level:
            stmt = stmt.where(Job.experience_level == experience_level)

        stmt = stmt.order_by(Job.posted_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_matches_for_resume(
        self, resume_id: UUID, limit: int = 20
    ) -> Sequence[JobMatch]:
        """Get job matches for a resume, ordered by score."""
        result = await self.db.execute(
            select(JobMatch)
            .where(JobMatch.resume_id == resume_id)
            .order_by(JobMatch.overall_score.desc())
            .limit(limit)
        )
        return result.scalars().all()
