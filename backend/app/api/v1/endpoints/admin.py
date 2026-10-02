"""
Admin dashboard endpoints.

All endpoints require admin role.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.auth import MessageResponse
from app.api.v1.schemas.user import UserListItem
from app.core.security import get_current_admin
from app.db.session import get_async_session
from app.models.analytics import AdminAuditLog
from app.models.chat import ChatSession
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User

router = APIRouter()


@router.get(
    "/dashboard",
    summary="Admin dashboard aggregate stats",
)
async def admin_dashboard(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Get aggregate platform statistics for the admin dashboard."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_resumes = (await db.execute(select(func.count(Resume.id)))).scalar() or 0
    total_jobs = (await db.execute(select(func.count(Job.id)))).scalar() or 0
    total_sessions = (await db.execute(select(func.count(ChatSession.id)))).scalar() or 0

    active_users = (
        await db.execute(select(func.count(User.id)).where(User.is_active == True))
    ).scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_resumes": total_resumes,
        "total_jobs": total_jobs,
        "total_chat_sessions": total_sessions,
    }


@router.get(
    "/users",
    response_model=list[UserListItem],
    summary="List all users",
)
async def list_users(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """List all registered users (paginated)."""
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.put(
    "/users/{user_id}/role",
    response_model=MessageResponse,
    summary="Change user role",
)
async def update_user_role(
    user_id: UUID,
    role: str = Query(..., pattern="^(user|admin)$"),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Change a user's role (user or admin)."""
    from app.core.exceptions import NotFoundException

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User", user_id)

    old_role = user.role
    user.role = role
    db.add(user)

    # Audit log
    audit = AdminAuditLog(
        admin_id=admin.id,
        action="change_role",
        resource_type="user",
        resource_id=user_id,
        changes={"old_role": old_role, "new_role": role},
    )
    db.add(audit)
    await db.flush()

    return MessageResponse(message=f"User role updated to '{role}'.")


@router.put(
    "/users/{user_id}/status",
    response_model=MessageResponse,
    summary="Activate/deactivate user",
)
async def update_user_status(
    user_id: UUID,
    is_active: bool = Query(...),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Activate or deactivate a user account."""
    from app.core.exceptions import NotFoundException

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User", user_id)

    user.is_active = is_active
    db.add(user)

    # Audit log
    audit = AdminAuditLog(
        admin_id=admin.id,
        action="change_status",
        resource_type="user",
        resource_id=user_id,
        changes={"is_active": is_active},
    )
    db.add(audit)
    await db.flush()

    action = "activated" if is_active else "deactivated"
    return MessageResponse(message=f"User {action} successfully.")
