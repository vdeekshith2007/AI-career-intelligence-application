"""
Skill repository — data access layer for Skill operations.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import Skill
from app.repositories.base import BaseRepository


class SkillRepository(BaseRepository[Skill]):
    """Skill-specific data access methods."""

    def __init__(self, db: AsyncSession):
        super().__init__(Skill, db)

    async def get_by_name(self, name: str) -> Skill | None:
        """Find a skill by exact name (case-insensitive)."""
        result = await self.db.execute(
            select(Skill).where(Skill.name.ilike(name))
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        query: str | None = None,
        category: str | None = None,
        limit: int = 100,
    ) -> Sequence[Skill]:
        """Search skills by name or category."""
        stmt = select(Skill).where(Skill.is_active == True)
        if query:
            stmt = stmt.where(Skill.name.ilike(f"%{query}%"))
        if category:
            stmt = stmt.where(Skill.category == category)
        stmt = stmt.order_by(Skill.name).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_or_create(self, name: str, category: str | None = None) -> Skill:
        """Get an existing skill by name or create a new one."""
        skill = await self.get_by_name(name)
        if skill:
            return skill
        return await self.create(name=name, category=category)
