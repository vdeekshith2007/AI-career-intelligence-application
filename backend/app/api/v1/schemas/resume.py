"""
Resume Pydantic schemas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ResumeResponse(BaseModel):
    """Resume response with parsed data."""

    id: UUID
    original_filename: str
    status: str
    parsed_data: dict[str, Any] | None = None
    contact_info: dict[str, Any] | None = None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeListItem(BaseModel):
    """Resume for list views."""

    id: UUID
    original_filename: str
    status: str
    version: int
    created_at: datetime
    parsed_data: dict[str, Any] | None = None
    contact_info: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class ATSScoreResponse(BaseModel):
    """ATS score response."""

    id: UUID
    resume_id: UUID
    job_id: UUID | None = None
    overall_score: float
    format_score: float | None = None
    keyword_score: float | None = None
    experience_score: float | None = None
    education_score: float | None = None
    impact_score: float | None = None
    section_feedback: dict[str, Any] | None = None
    improvement_suggestions: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ATSScoreRequest(BaseModel):
    """Request to score a resume against a specific job description."""

    job_description: str | None = None
    job_id: UUID | None = None
