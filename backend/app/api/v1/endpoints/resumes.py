"""
Resume management endpoints.

Handles upload, listing, retrieval, deletion, and ATS scoring.
"""

import hashlib
import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.auth import MessageResponse
from app.api.v1.schemas.resume import (
    ATSScoreRequest,
    ATSScoreResponse,
    ResumeListItem,
    ResumeResponse,
)
from app.config import get_settings
from app.core.exceptions import NotFoundException
from app.core.security import get_current_user
from app.db.session import get_async_session
from app.models.resume import Resume
from app.models.user import User
from app.services.ats_scorer import score_resume
from app.services.resume_parser import (
    extract_resume_text,
    parse_full_resume,
    save_parsed_resume_to_db,
    validate_resume_upload,
)

router = APIRouter()
settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a resume",
)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Upload a PDF or DOCX resume with validation, text extraction, parsing, and database storage."""
    # 1. Read file content
    content = await file.read()

    # 2. File validation (extension, size, and header integrity)
    ext = validate_resume_upload(
        filename=file.filename,
        content=content,
        max_bytes=settings.max_upload_bytes,
    )

    # 3. Text extraction & sanitization
    raw_text = extract_resume_text(content, ext)

    # 4. Resume parsing (contact info, skills, education, projects, experience, summary)
    parsed_result = parse_full_resume(raw_text)

    # 5. Generate file hash for deduplication
    file_hash = hashlib.sha256(content).hexdigest()

    # 6. Save physical file to disk
    user_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(user_dir, exist_ok=True)

    file_path = os.path.join(user_dir, f"{file_hash}{ext}")
    with open(file_path, "wb") as f:
        f.write(content)

    # 7. Determine version
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    version = (latest.version + 1) if latest else 1

    # 8. Create initial resume record
    resume = Resume(
        user_id=current_user.id,
        original_filename=file.filename,
        file_path=file_path,
        file_hash=file_hash,
        status="uploaded",
        version=version,
    )
    db.add(resume)
    await db.flush()

    # 9. Persist parsed information & link canonical skills
    resume = await save_parsed_resume_to_db(
        db=db,
        resume=resume,
        raw_text=raw_text,
        parsed_result=parsed_result,
    )

    return resume


@router.get(
    "",
    response_model=list[ResumeListItem],
    include_in_schema=False,
)
@router.get(
    "/",
    response_model=list[ResumeListItem],
    summary="List user's resumes",
)
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get all resumes uploaded by the current user."""
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
    )
    return result.scalars().all()


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="Get resume details",
)
async def get_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get a specific resume with parsed data."""
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise NotFoundException("Resume", resume_id)
    return resume


@router.delete(
    "/{resume_id}",
    response_model=MessageResponse,
    summary="Delete a resume",
)
async def delete_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Delete a resume and its associated file."""
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise NotFoundException("Resume", resume_id)

    # Delete physical file
    if os.path.exists(resume.file_path):
        os.remove(resume.file_path)

    await db.delete(resume)
    await db.flush()

    return MessageResponse(message="Resume deleted successfully.")


def _extract_resume_text(file_path: str) -> str:
    """Extract text from PDF or DOCX file using parser service."""
    if not os.path.exists(file_path):
        return ""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        with open(file_path, "rb") as f:
            return extract_resume_text(f.read(), ext)
    except Exception:
        return ""


@router.post(
    "/{resume_id}/analyze",
    response_model=ATSScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze resume and generate ATS score",
)
async def analyze_resume(
    resume_id: UUID,
    payload: ATSScoreRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Analyze a resume's content, formatting, and industry keywords."""
    from app.models.analytics import ATSScore

    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise NotFoundException("Resume", resume_id)

    raw_text = resume.raw_text or _extract_resume_text(resume.file_path)

    # Resolve target job description if provided via payload or job_id
    target_jd = payload.job_description if payload and payload.job_description else None
    if not target_jd and payload and payload.job_id:
        from app.models.job import Job

        job_result = await db.execute(select(Job).where(Job.id == payload.job_id))
        job_obj = job_result.scalar_one_or_none()
        if job_obj:
            jd_parts = [f"{job_obj.title} at {job_obj.company}"]
            if job_obj.description:
                jd_parts.append(job_obj.description)
            if job_obj.requirements:
                jd_parts.append(job_obj.requirements)
            target_jd = "\n".join(jd_parts)

    # Calculate deterministic multi-dimensional ATS score
    scoring_result = score_resume(
        raw_text=raw_text,
        parsed_data=resume.parsed_data,
        job_description=target_jd,
    )

    # Save score record
    score_entry = ATSScore(
        resume_id=resume.id,
        job_id=payload.job_id if payload else None,
        overall_score=scoring_result["overall_score"],
        format_score=scoring_result["format_score"],
        keyword_score=scoring_result["keyword_score"],
        experience_score=scoring_result["experience_score"],
        education_score=scoring_result["education_score"],
        impact_score=scoring_result["impact_score"],
        section_feedback=scoring_result["section_feedback"],
        improvement_suggestions=scoring_result["improvement_suggestions"],
    )
    db.add(score_entry)

    # Update resume status and augment parsed data without losing existing parsed structure
    resume.status = "analyzed"
    updated_parsed = dict(resume.parsed_data) if resume.parsed_data else {}
    updated_parsed.update({
        "word_count": len(raw_text.split()),
        "keywords_detected": scoring_result["improvement_suggestions"].get("keywords_found", []),
        "matching_skills": scoring_result["improvement_suggestions"].get("matching_skills", []),
        "missing_skills": scoring_result["improvement_suggestions"].get("missing_skills", []),
        "sections_detected": {
            "contact": scoring_result["format_score"] > 0,
            "experience": scoring_result["experience_score"] > 0,
            "education": scoring_result["education_score"] > 0,
            "skills": scoring_result["keyword_score"] > 0,
        },
    })
    resume.parsed_data = updated_parsed
    db.add(resume)
    await db.flush()
    await db.refresh(score_entry)

    return score_entry


@router.get(
    "/{resume_id}/analysis",
    response_model=ATSScoreResponse,
    summary="Get latest ATS analysis for a resume",
)
async def get_resume_analysis(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Retrieve the most recent ATS score and feedback for a resume."""
    from app.models.analytics import ATSScore

    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise NotFoundException("Resume", resume_id)

    score_result = await db.execute(
        select(ATSScore)
        .where(ATSScore.resume_id == resume_id)
        .order_by(ATSScore.created_at.desc())
        .limit(1)
    )
    score_entry = score_result.scalar_one_or_none()
    if not score_entry:
        raise NotFoundException("ATS Score for Resume", resume_id)

    return score_entry
