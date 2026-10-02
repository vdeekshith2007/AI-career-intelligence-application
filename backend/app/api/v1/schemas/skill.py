"""
Skill Pydantic schemas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SkillResponse(BaseModel):
    """Skill response."""

    id: UUID
    name: str
    category: str | None = None
    subcategory: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class GapAnalysisRequest(BaseModel):
    """Request to run a skill gap analysis."""

    resume_id: UUID
    target_role: str = Field(..., min_length=2, max_length=255)


class SkillGapResponse(BaseModel):
    """Individual skill gap."""

    skill_name: str
    current_level: str
    required_level: str
    priority_rank: int
    recommendation: str | None = None


class GapAnalysisResponse(BaseModel):
    """Skill gap analysis result."""

    id: UUID
    target_role: str
    readiness_score: float | None = None
    gaps: list[SkillGapResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class RoadmapRequest(BaseModel):
    """Request to generate a learning roadmap."""

    assessment_id: UUID


class RoadmapResponse(BaseModel):
    """Learning roadmap response."""

    id: UUID
    target_role: str
    estimated_weeks: int | None = None
    phases: dict[str, Any] | None = None
    milestones: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
