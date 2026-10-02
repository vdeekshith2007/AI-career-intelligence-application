"""
Skill, SkillAssessment, SkillGap, and LearningRoadmap ORM models.
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.job import JobSkill
    from app.models.resume import ResumeSkill
    from app.models.user import User


class Skill(Base, UUIDMixin, TimestampMixin):
    """Canonical skill entity (shared across resumes and jobs)."""

    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    aliases: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # --- Relationships ---
    resume_skills: Mapped[list["ResumeSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan", lazy="selectin"
    )
    job_skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Skill(id={self.id}, name={self.name})>"


class SkillAssessment(Base, UUIDMixin, TimestampMixin):
    """Skill gap assessment for a user targeting a specific role."""

    __tablename__ = "skill_assessments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    current_skills: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    required_skills: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    readiness_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Relationships ---
    user: Mapped["User"] = relationship(back_populates="skill_assessments")
    gaps: Mapped[list["SkillGap"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", lazy="selectin"
    )
    roadmaps: Mapped[list["LearningRoadmap"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<SkillAssessment(user={self.user_id}, role={self.target_role})>"


class SkillGap(Base, UUIDMixin):
    """Individual skill gap within an assessment."""

    __tablename__ = "skill_gaps"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skill_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    current_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="none"
    )
    required_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="intermediate"
    )
    priority_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    assessment: Mapped["SkillAssessment"] = relationship(back_populates="gaps")

    def __repr__(self) -> str:
        return f"<SkillGap(assessment={self.assessment_id}, skill={self.skill_id})>"


class LearningRoadmap(Base, UUIDMixin, TimestampMixin):
    """AI-generated learning roadmap to close skill gaps."""

    __tablename__ = "learning_roadmaps"

    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skill_assessments.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    estimated_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phases: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    milestones: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resources: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="generated", server_default="generated"
    )

    # --- Relationships ---
    assessment: Mapped[Optional["SkillAssessment"]] = relationship(back_populates="roadmaps")
    user: Mapped["User"] = relationship(back_populates="learning_roadmaps")

    def __repr__(self) -> str:
        return f"<LearningRoadmap(user={self.user_id}, role={self.target_role})>"
