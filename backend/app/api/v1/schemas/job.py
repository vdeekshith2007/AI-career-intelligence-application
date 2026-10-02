"""
Job Pydantic schemas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    """Job listing response."""

    id: UUID
    title: str
    company: str
    location: str | None = None
    work_type: str
    description: str | None = None
    requirements: str | None = None
    salary_range: str | None = None
    experience_level: str
    source_url: str | None = None
    is_active: bool
    posted_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    """Compact job for list views."""

    id: UUID
    title: str
    company: str
    location: str | None = None
    work_type: str
    salary_range: str | None = None
    experience_level: str
    is_active: bool
    posted_at: datetime | None = None

    model_config = {"from_attributes": True}


class JobMatchResponse(BaseModel):
    """Job match result."""

    id: UUID
    job: JobListItem
    overall_score: float
    score_breakdown: dict[str, Any] | None = None
    matching_skills: dict[str, Any] | None = None
    missing_skills: dict[str, Any] | None = None
    recommendation: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobSearchParams(BaseModel):
    """Job search filter parameters."""

    query: str | None = None
    location: str | None = None
    work_type: str | None = None
    experience_level: str | None = None
    cursor: str | None = None
    limit: int = Field(20, ge=1, le=50)
