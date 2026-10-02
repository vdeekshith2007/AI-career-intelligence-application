"""
Advanced AI Job Matching Engine.

Provides multi-dimensional scoring and personalized career recommendations:
1. Skill Overlap & Coverage (40%) — Exact and taxonomy-based skill intersection
2. Semantic & Keyword Alignment (25%) — Contextual domain and keyword relevance
3. Experience & Seniority Level (20%) — Seniority calibration (Junior -> Executive)
4. Role Title & Domain Alignment (15%) — Direct role matching

Outputs actionable skill gap analysis and customized resume tailoring advice.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobMatch
from app.models.resume import Resume
from app.services.resume_parser import extract_skills

logger = logging.getLogger(__name__)

# Seniority ladder mapping for experience level matching
EXPERIENCE_HIERARCHY: dict[str, int] = {
    "intern": 0,
    "entry": 1,
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "lead": 4,
    "staff": 4,
    "principal": 5,
    "director": 5,
    "executive": 6,
}


def _normalize_skill(skill: str) -> str:
    """Normalize skill string for robust comparison."""
    s = skill.strip().lower()
    # Normalize common synonyms
    synonyms = {
        "reactjs": "react",
        "react.js": "react",
        "nextjs": "next.js",
        "nodejs": "node.js",
        "node": "node.js",
        "postgres": "postgresql",
        "aws cloud": "aws",
        "rest api": "rest",
        "restful api": "rest",
        "k8s": "kubernetes",
        "golang": "go",
        "python3": "python",
        "ts": "typescript",
        "js": "javascript",
    }
    return synonyms.get(s, s)


def _extract_candidate_skills(resume: Resume) -> set[str]:
    """Extract full set of normalized skills from parsed resume or raw text."""
    skills_set: set[str] = set()

    # 1. Check parsed_data skills (JSON field, already in memory)
    if resume.parsed_data and isinstance(resume.parsed_data, dict):
        skills_block = resume.parsed_data.get("skills")
        if isinstance(skills_block, dict):
            all_skills = skills_block.get("all", [])
            for sk in all_skills:
                skills_set.add(_normalize_skill(str(sk)))

    # 2. Extract from raw text if parsed data is sparse
    if len(skills_set) < 5 and resume.raw_text:
        extracted = extract_skills(resume.raw_text)
        for sk in extracted.get("all", []):
            skills_set.add(_normalize_skill(str(sk)))

    return skills_set


def _extract_job_skills(job: Job) -> set[str]:
    """Extract required and preferred skills from a job listing."""
    job_skills: set[str] = set()

    # Extract directly from title, requirements and description text (in memory)
    combined_text = f"{job.title} {job.requirements or ''} {job.description or ''}"
    extracted = extract_skills(combined_text)
    for sk in extracted.get("all", []):
        job_skills.add(_normalize_skill(str(sk)))

    return job_skills


def _estimate_candidate_seniority(resume: Resume) -> str:
    """Estimate candidate seniority level based on work experience and titles."""
    text = (resume.raw_text or "").lower()

    if any(k in text for k in ["vp of", "chief", "director", "head of", "principal engineer"]):
        return "lead"
    if any(k in text for k in ["senior", "lead", "architect", "staff engineer"]):
        return "senior"
    if any(k in text for k in ["mid-level", "software engineer ii", "3+ years", "4+ years"]):
        return "mid"
    if any(k in text for k in ["junior", "associate", "entry", "intern", "graduate"]):
        return "entry"

    # Count years of experience heuristics
    year_matches = re.findall(r"(\d+)\+?\s*years?(?:\s+of)?\s+experience", text)
    if year_matches:
        try:
            max_years = max(int(y) for y in year_matches)
            if max_years >= 7:
                return "lead"
            if max_years >= 4:
                return "senior"
            if max_years >= 2:
                return "mid"
            return "entry"
        except ValueError:
            pass

    return "mid"


def calculate_job_match(resume: Resume, job: Job) -> dict[str, Any]:
    """
    Calculate multi-dimensional match score between a candidate resume and a job listing.

    Returns:
        dict with overall_score, score_breakdown, matching_skills, missing_skills, recommendation
    """
    cand_skills = _extract_candidate_skills(resume)
    job_skills = _extract_job_skills(job)

    # -------------------------------------------------------------------------
    # Dimension 1: Skill Overlap & Coverage (40%)
    # -------------------------------------------------------------------------
    matching_skills = sorted(list(cand_skills.intersection(job_skills)))
    missing_skills = sorted(list(job_skills.difference(cand_skills)))

    if job_skills:
        skill_coverage = len(matching_skills) / len(job_skills)
        # Bonus for extra relevant candidate skills
        extra_skills = len(cand_skills) - len(matching_skills)
        bonus = min(extra_skills * 0.02, 0.15)
        skill_score = min((skill_coverage + bonus) * 100.0, 100.0)
    else:
        # If job lists no specific skills, evaluate general technical density
        skill_score = min(len(cand_skills) * 8.0, 85.0)

    # -------------------------------------------------------------------------
    # Dimension 2: Semantic & Domain Alignment (25%)
    # -------------------------------------------------------------------------
    job_corpus = f"{job.title} {job.description or ''} {job.requirements or ''}".lower()
    resume_corpus = (resume.raw_text or "").lower()

    # Identify domain focus
    domains = {
        "backend": ["api", "database", "sql", "fastapi", "django", "server", "microservice", "python"],
        "frontend": ["react", "next.js", "ui", "css", "tailwind", "typescript", "frontend", "web"],
        "devops": ["docker", "kubernetes", "ci/cd", "aws", "cloud", "terraform", "infrastructure"],
        "ai_ml": ["machine learning", "rag", "llm", "deep learning", "nlp", "vector", "langchain"],
        "data": ["data pipeline", "etl", "analytics", "postgresql", "big data", "spark"],
    }

    job_domains = {d for d, terms in domains.items() if any(t in job_corpus for t in terms)}
    cand_domains = {d for d, terms in domains.items() if any(t in resume_corpus for t in terms)}

    if job_domains:
        domain_overlap = len(job_domains.intersection(cand_domains)) / len(job_domains)
        semantic_score = round(domain_overlap * 100.0, 1)
    else:
        semantic_score = 75.0

    # -------------------------------------------------------------------------
    # Dimension 3: Experience & Seniority Calibration (20%)
    # -------------------------------------------------------------------------
    cand_seniority = _estimate_candidate_seniority(resume)
    job_level = (job.experience_level or "mid").lower()

    cand_rank = EXPERIENCE_HIERARCHY.get(cand_seniority, 2)
    job_rank = EXPERIENCE_HIERARCHY.get(job_level, 2)
    rank_diff = abs(cand_rank - job_rank)

    if rank_diff == 0:
        experience_score = 100.0
    elif rank_diff == 1:
        # Adjacent level (e.g. mid applying to senior or vice versa)
        experience_score = 82.0
    elif rank_diff == 2:
        experience_score = 55.0
    else:
        experience_score = 30.0

    # -------------------------------------------------------------------------
    # Dimension 4: Role Title Alignment (15%)
    # -------------------------------------------------------------------------
    job_title_words = set(re.findall(r"\w+", job.title.lower()))
    resume_title_words = set(re.findall(r"\w+", resume_corpus[:500]))  # Header area

    common_title_tokens = job_title_words.intersection(resume_title_words)
    # Exclude stop words
    common_title_tokens = {w for w in common_title_tokens if len(w) > 2 and w not in {"the", "and", "for", "with"}}

    if job_title_words:
        title_score = min(len(common_title_tokens) * 35.0, 100.0)
    else:
        title_score = 70.0

    # -------------------------------------------------------------------------
    # Composite Weighted Overall Score
    # -------------------------------------------------------------------------
    overall_score = round(
        (skill_score * 0.40)
        + (semantic_score * 0.25)
        + (experience_score * 0.20)
        + (title_score * 0.15),
        1,
    )
    overall_score = max(5.0, min(overall_score, 99.0))

    # -------------------------------------------------------------------------
    # Actionable Tailoring Recommendations
    # -------------------------------------------------------------------------
    recs: list[str] = []

    if missing_skills:
        top_missing = missing_skills[:4]
        recs.append(
            f"Add or highlight target skills required by this role: {', '.join(top_missing)}."
        )

    if rank_diff > 1 and cand_rank < job_rank:
        recs.append(
            f"This role seeks a {job_level.title()} professional. Feature lead projects, mentoring, and system architecture in your experience bullets."
        )
    elif rank_diff == 0:
        recs.append(
            f"Your experience level aligns directly with this {job_level.title()} position."
        )

    if matching_skills:
        top_matched = matching_skills[:3]
        recs.append(
            f"Strong match on core qualifications ({', '.join(top_matched)}). Place these prominently in your skills and summary section."
        )

    if not recs:
        recs.append("Great overall fit. Tailor your resume summary to mirror the company mission and target responsibilities.")

    recommendation_text = " ".join(recs)

    return {
        "overall_score": overall_score,
        "score_breakdown": {
            "skills_score": round(skill_score, 1),
            "semantic_score": round(semantic_score, 1),
            "experience_score": round(experience_score, 1),
            "title_score": round(title_score, 1),
        },
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "recommendation": recommendation_text,
    }


async def get_ranked_job_recommendations(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Get top AI-matched job recommendations for a user.

    If user has an uploaded resume, performs multi-dimensional ranking.
    If no resume exists, returns active jobs with baseline relevance.
    """
    # 1. Fetch user's latest active resume
    resume_stmt = (
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    resume_res = await db.execute(resume_stmt)
    latest_resume = resume_res.scalar_one_or_none()

    # 2. Fetch active jobs
    jobs_stmt = select(Job).where(Job.is_active == True).limit(50)
    jobs_res = await db.execute(jobs_stmt)
    active_jobs = jobs_res.scalars().all()

    if not active_jobs:
        return []

    # If user has no resume uploaded, return standard active jobs
    if not latest_resume:
        return [
            {
                "job": j,
                "match_score": None,
                "score_breakdown": None,
                "matching_skills": [],
                "missing_skills": [],
                "recommendation": "Upload a resume in the Resume Analyzer to calculate your personalized ATS match score and skill gaps.",
            }
            for j in active_jobs[:limit]
        ]

    # Calculate match for all active jobs
    matches: list[dict[str, Any]] = []
    for job in active_jobs:
        match_data = calculate_job_match(latest_resume, job)
        matches.append(
            {
                "job": job,
                "match_score": match_data["overall_score"],
                "score_breakdown": match_data["score_breakdown"],
                "matching_skills": match_data["matching_skills"],
                "missing_skills": match_data["missing_skills"],
                "recommendation": match_data["recommendation"],
            }
        )

    # Sort descending by match score
    matches.sort(key=lambda m: m["match_score"] or 0.0, reverse=True)

    return matches[:limit]
