"""
Job ORM models.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.resume import Resume
    from app.models.skill import Skill


class Job(Base, UUIDMixin, TimestampMixin):
    """Job listing model."""

    __tablename__ = "jobs"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="remote"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    experience_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="mid"
    )
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- Relationships ---
    required_skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", lazy="selectin"
    )
    matches: Mapped[list["JobMatch"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, title={self.title}, company={self.company})>"


class JobSkill(Base, UUIDMixin):
    """Junction table linking jobs to required skills."""

    __tablename__ = "job_skills"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    importance: Mapped[str] = mapped_column(
        String(20), nullable=False, default="important"
    )

    # --- Relationships ---
    job: Mapped["Job"] = relationship(back_populates="required_skills")
    skill: Mapped["Skill"] = relationship(back_populates="job_skills")

    def __repr__(self) -> str:
        return f"<JobSkill(job_id={self.job_id}, skill_id={self.skill_id})>"


class JobMatch(Base, UUIDMixin, TimestampMixin):
    """AI-generated job match results."""

    __tablename__ = "job_matches"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    matching_skills: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    missing_skills: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    resume: Mapped["Resume"] = relationship(back_populates="job_matches")
    job: Mapped["Job"] = relationship(back_populates="matches")

    def __repr__(self) -> str:
        return f"<JobMatch(resume={self.resume_id}, job={self.job_id}, score={self.overall_score})>"
