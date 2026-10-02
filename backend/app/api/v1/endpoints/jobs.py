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
from app.models.resume import Resume
from app.models.user import User
from app.services.job_matcher import calculate_job_match, get_ranked_job_recommendations

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
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get AI-recommended and ranked job listings based on candidate's uploaded resume.

    Evaluates jobs across Skill Overlap, Semantic Fit, Seniority Calibration,
    and Role Alignment, providing actionable skill gaps and resume tailoring tips.
    """
    ranked = await get_ranked_job_recommendations(db, current_user.id, limit=limit)
    response_items: list[JobListItem] = []
    for item in ranked:
        j = item["job"]
        response_items.append(
            JobListItem(
                id=j.id,
                title=j.title,
                company=j.company,
                location=j.location,
                work_type=j.work_type,
                salary_range=j.salary_range,
                experience_level=j.experience_level,
                is_active=j.is_active,
                posted_at=j.posted_at,
                match_score=item["match_score"],
                score_breakdown=item["score_breakdown"],
                matching_skills=item["matching_skills"],
                missing_skills=item["missing_skills"],
                recommendation=item["recommendation"],
            )
        )
    return response_items


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


@router.get(
    "/{job_id}/match",
    summary="Get deep AI match analysis for a job",
)
async def get_job_match(
    job_id: UUID,
    resume_id: UUID | None = Query(None, description="Specific resume ID to evaluate against"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Perform on-demand deep-dive AI matching analysis for a specific job.

    Returns multidimensional score breakdown, matching skills, missing skills (gap),
    and personalized resume tailoring recommendations.
    """
    # 1. Fetch job
    job_res = await db.execute(select(Job).where(Job.id == job_id))
    job = job_res.scalar_one_or_none()
    if not job:
        raise NotFoundException("Job", job_id)

    # 2. Fetch target resume
    if resume_id:
        res_stmt = select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    else:
        res_stmt = (
            select(Resume)
            .where(Resume.user_id == current_user.id)
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
    res_result = await db.execute(res_stmt)
    resume = res_result.scalar_one_or_none()

    if not resume:
        return {
            "job_id": str(job.id),
            "job_title": job.title,
            "company": job.company,
            "overall_score": None,
            "status": "no_resume",
            "message": "Upload a resume first to run automated ATS skill matching.",
        }

    match_result = calculate_job_match(resume, job)
    return {
        "job_id": str(job.id),
        "job_title": job.title,
        "company": job.company,
        "resume_id": str(resume.id),
        **match_result,
    }
