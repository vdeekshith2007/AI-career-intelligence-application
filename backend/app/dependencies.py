"""
Shared FastAPI dependencies.

Provides commonly injected dependencies such as database sessions and current user.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_async_session
from app.models.user import User

# Type aliases for clean dependency injection
DBSession = Annotated[AsyncSession, Depends(get_async_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
