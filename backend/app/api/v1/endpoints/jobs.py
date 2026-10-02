"""
Job listing endpoints.

Handles job search, details, matching, and application tracking.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.job import JobListItem, JobResponse
from app.core.exceptions import NotFoundException
from app.core.security import get_current_user
from app.db.session import get_async_session
from app.models.job import Job
from app.models.user import User

router = APIRouter()


@router.get(
    "",
    response_model=list[JobListItem],
    include_in_schema=False,
)
@router.get(
    "/",
    response_model=list[JobListItem],
    summary="Search and list jobs",
)
async def list_jobs(
    query: str | None = Query(None),
    location: str | None = Query(None),
    work_type: str | None = Query(None),
    experience_level: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Search and filter active job listings."""
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

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/recommendations",
    response_model=list[JobListItem],
    summary="Get AI-recommended jobs",
)
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get AI-recommended job listings based on the user's resume and skills.

    TODO: Implement via Job Matcher Agent in Phase 3.
    """
    # Return recent active jobs
    result = await db.execute(
        select(Job)
        .where(Job.is_active == True)
        .order_by(Job.posted_at.desc())
        .limit(10)
    )
    return result.scalars().all()


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job details",
)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get detailed information about a specific job listing."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise NotFoundException("Job", job_id)
    return job
