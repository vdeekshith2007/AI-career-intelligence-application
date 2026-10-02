"""
Analytics, audit, ATS scoring, and job application ORM models.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.resume import Resume
    from app.models.user import User


class ATSScore(Base, UUIDMixin, TimestampMixin):
    """ATS (Applicant Tracking System) score for a resume."""

    __tablename__ = "ats_scores"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    format_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    keyword_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    education_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    impact_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    section_feedback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    improvement_suggestions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # --- Relationships ---
    resume: Mapped["Resume"] = relationship(back_populates="ats_scores")

    def __repr__(self) -> str:
        return f"<ATSScore(resume={self.resume_id}, score={self.overall_score})>"


class JobApplication(Base, UUIDMixin, TimestampMixin):
    """User's tracked job application."""

    __tablename__ = "job_applications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="interested", server_default="interested"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- Relationships ---
    user: Mapped["User"] = relationship(back_populates="job_applications")

    def __repr__(self) -> str:
        return f"<JobApplication(user={self.user_id}, job={self.job_id}, status={self.status})>"


class AnalyticsEvent(Base, UUIDMixin):
    """Append-only analytics event log."""

    __tablename__ = "analytics_events"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    def __repr__(self) -> str:
        return f"<AnalyticsEvent(type={self.event_type}, user={self.user_id})>"


class AdminAuditLog(Base, UUIDMixin):
    """Audit trail for admin actions."""

    __tablename__ = "admin_audit_log"

    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    def __repr__(self) -> str:
        return f"<AdminAuditLog(admin={self.admin_id}, action={self.action})>"
