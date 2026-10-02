"""
Generic base repository with common CRUD operations.

All entity-specific repositories extend this base class.
"""

from collections.abc import Sequence
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository[ModelType: Base]:
    """
    Base repository providing reusable CRUD operations.

    Usage:
        class UserRepo(BaseRepository[User]):
            def __init__(self, db: AsyncSession):
                super().__init__(User, db)
    """

    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, record_id: UUID) -> ModelType | None:
        """Get a single record by primary key."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: Any = None,
    ) -> Sequence[ModelType]:
        """Get multiple records with pagination."""
        stmt = select(self.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(self, instance: ModelType, **kwargs: Any) -> ModelType:
        """Update an existing record."""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Delete a record."""
        await self.db.delete(instance)
        await self.db.flush()

    async def count(self) -> int:
        """Count total records."""
        result = await self.db.execute(select(func.count(self.model.id)))
        return result.scalar() or 0

    async def exists(self, record_id: UUID) -> bool:
        """Check if a record exists by ID."""
        result = await self.db.execute(
            select(func.count()).where(self.model.id == record_id)
        )
        return (result.scalar() or 0) > 0
