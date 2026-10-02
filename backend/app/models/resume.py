"""
Resume ORM models.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.analytics import ATSScore
    from app.models.job import JobMatch
    from app.models.skill import Skill
    from app.models.user import User


class Resume(Base, UUIDMixin, TimestampMixin):
    """Uploaded resume model."""

    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uploaded", server_default="uploaded"
    )
    parsed_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    contact_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # --- Relationships ---
    user: Mapped["User"] = relationship(back_populates="resumes")
    skills: Mapped[list["ResumeSkill"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", lazy="selectin"
    )
    ats_scores: Mapped[list["ATSScore"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", lazy="selectin"
    )
    job_matches: Mapped[list["JobMatch"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, filename={self.original_filename}, status={self.status})>"


class ResumeSkill(Base, UUIDMixin):
    """Junction table linking resumes to skills with proficiency metadata."""

    __tablename__ = "resume_skills"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    proficiency: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default="intermediate"
    )
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # --- Relationships ---
    resume: Mapped["Resume"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(back_populates="resume_skills")

    def __repr__(self) -> str:
        return f"<ResumeSkill(resume_id={self.resume_id}, skill_id={self.skill_id})>"
