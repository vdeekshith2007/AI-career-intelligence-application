"""
Skill gap analysis and learning roadmap endpoints.

TODO: Full implementation connects to Skill Analyzer and Roadmap Generator agents.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.skill import (
    GapAnalysisRequest,
    GapAnalysisResponse,
    RoadmapResponse,
    SkillResponse,
)
from app.core.exceptions import NotFoundException
from app.core.security import get_current_user
from app.db.session import get_async_session
from app.models.skill import LearningRoadmap, Skill, SkillAssessment
from app.models.user import User

router = APIRouter()


@router.get(
    "/",
    response_model=list[SkillResponse],
    summary="List all skills",
)
async def list_skills(
    search: str | None = None,
    category: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List all available skills, optionally filtered by search query or category."""
    stmt = select(Skill).where(Skill.is_active == True)

    if search:
        stmt = stmt.where(Skill.name.ilike(f"%{search}%"))
    if category:
        stmt = stmt.where(Skill.category == category)

    stmt = stmt.order_by(Skill.name).limit(100)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post(
    "/gap-analysis",
    response_model=GapAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run skill gap analysis",
)
async def create_gap_analysis(
    payload: GapAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Analyze skill gaps between the user's resume and a target role.

    TODO: Connect to Skill Analyzer Agent in Phase 4.
    """
    assessment = SkillAssessment(
        user_id=current_user.id,
        resume_id=payload.resume_id,
        target_role=payload.target_role,
    )
    db.add(assessment)
    await db.flush()
    await db.refresh(assessment)

    # TODO: Trigger Skill Analyzer Agent asynchronously
    # await trigger_skill_analysis(assessment.id)

    return GapAnalysisResponse(
        id=assessment.id,
        target_role=assessment.target_role,
        readiness_score=None,
        gaps=[],
        created_at=assessment.created_at,
    )


@router.get(
    "/gap-analysis/{assessment_id}",
    response_model=GapAnalysisResponse,
    summary="Get gap analysis results",
)
async def get_gap_analysis(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get the results of a previously run skill gap analysis."""
    result = await db.execute(
        select(SkillAssessment).where(
            SkillAssessment.id == assessment_id,
            SkillAssessment.user_id == current_user.id,
        )
    )
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise NotFoundException("Skill Assessment", assessment_id)

    return GapAnalysisResponse(
        id=assessment.id,
        target_role=assessment.target_role,
        readiness_score=assessment.readiness_score,
        gaps=[],  # TODO: populate from SkillGap records
        created_at=assessment.created_at,
    )


@router.get(
    "/roadmap/{roadmap_id}",
    response_model=RoadmapResponse,
    summary="Get learning roadmap",
)
async def get_roadmap(
    roadmap_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get a generated learning roadmap."""
    result = await db.execute(
        select(LearningRoadmap).where(
            LearningRoadmap.id == roadmap_id,
            LearningRoadmap.user_id == current_user.id,
        )
    )
    roadmap = result.scalar_one_or_none()
    if not roadmap:
        raise NotFoundException("Learning Roadmap", roadmap_id)
    return roadmap
