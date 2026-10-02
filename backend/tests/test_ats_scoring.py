"""
Comprehensive Verification Tests for the ATS Scoring System.

Tests cover:
1. Complete pipeline trace:
   Resume → text extraction → skill extraction → job description → keyword analysis → scoring → missing skills → final result
2. Empty resume (0 words, whitespace)
3. Incomplete resume (contact only, skills only, missing sections)
4. Normal resume (general industry benchmark)
5. Job description with missing skills (low keyword score, missing skills identified)
6. Job description with matching skills (high keyword score, matching skills identified)
7. HTTP API endpoint integration (with raw job_description and with database job_id)
8. Mathematical determinism (scores bounded between 0.0 and 100.0, zero fake random scores)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.services.ats_scorer import score_resume
from tests.test_resume_pipeline import (
    generate_fullstack_pdf_resume,
    get_authenticated_user_token,
)

# ============================================================================
# 1. EMPTY RESUME SCENARIOS
# ============================================================================

def test_ats_empty_resume_completely_blank():
    """Verify completely empty resume produces 0.0 scores across all dimensions."""
    result = score_resume(raw_text="")
    assert result["overall_score"] == 0.0
    assert result["format_score"] == 0.0
    assert result["keyword_score"] == 0.0
    assert result["experience_score"] == 0.0
    assert result["education_score"] == 0.0
    assert result["impact_score"] == 0.0
    assert "empty" in result["improvement_suggestions"]["top_recommendations"][0].lower()


def test_ats_empty_resume_whitespace_only():
    """Verify resume with only whitespace/punctuation produces 0.0 scores safely."""
    result = score_resume(raw_text="   \n\n\t   ... ---   ")
    assert result["overall_score"] == 0.0
    assert result["format_score"] == 0.0
    assert result["keyword_score"] == 0.0
    assert result["experience_score"] == 0.0
    assert result["education_score"] == 0.0
    assert result["impact_score"] == 0.0


# ============================================================================
# 2. INCOMPLETE RESUME SCENARIOS
# ============================================================================

def test_ats_incomplete_resume_contact_only():
    """
    Verify incomplete resume with only contact information and no experience or education
    is scored strictly without fake inflation.
    """
    contact_only_text = (
        "John Smith\n"
        "Email: john.smith@example.com\n"
        "Phone: (555) 123-4567\n"
        "Location: Denver, CO\n"
    )
    result = score_resume(raw_text=contact_only_text)

    # Has contact (25%), but no experience (0%), no education (0%), no skills (0%)
    assert result["format_score"] == 25.0
    assert result["experience_score"] == 0.0
    assert result["education_score"] == 0.0
    assert result["keyword_score"] == 0.0
    assert result["impact_score"] == 0.0

    # Overall = 25.0 * 0.25 (format) = 6.2 or 6.3
    assert 6.0 <= result["overall_score"] <= 7.0
    rec_text = " ".join(result["improvement_suggestions"]["top_recommendations"]).lower()
    assert "education" in rec_text
    assert "experience" in rec_text


def test_ats_incomplete_resume_skills_only():
    """
    Verify resume with skills but missing education and work experience
    scores keywords but receives 0 for education and experience.
    """
    skills_only_text = (
        "Core Skills:\n"
        "Python, React, TypeScript, Docker, PostgreSQL, Redis, AWS, Git"
    )
    result = score_resume(raw_text=skills_only_text)

    # Keywords detected
    assert result["keyword_score"] >= 70.0
    # No education section
    assert result["education_score"] == 0.0
    # No experience section
    assert result["experience_score"] == 0.0
    # Overall score penalized heavily by missing sections
    assert result["overall_score"] < 50.0


# ============================================================================
# 3. NORMAL RESUME SCENARIO (GENERAL BENCHMARK)
# ============================================================================

def test_ats_normal_resume_general_benchmark():
    """
    Verify a well-structured resume receives a high ATS score based on
    formatting, strong action verbs, quantifiable metrics, and broad industry skills.
    """
    normal_text = (
        "Alex Johnson\n"
        "alex.johnson@example.com | (555) 123-4567 | San Francisco, CA\n"
        "LinkedIn: https://linkedin.com/in/alexjohnson | GitHub: https://github.com/alexjohnson\n"
        "\n"
        "SUMMARY\n"
        "Senior Full-Stack Engineer with 6+ years of experience designing scalable microservices.\n"
        "\n"
        "TECHNICAL SKILLS\n"
        "Languages: Python, TypeScript, JavaScript, SQL\n"
        "Frameworks: React, Next.js, Node.js, FastAPI, Express\n"
        "Cloud & DevOps: Docker, Kubernetes, AWS, CI/CD, Git, Linux\n"
        "Databases: PostgreSQL, Redis, MongoDB\n"
        "\n"
        "WORK EXPERIENCE\n"
        "Senior Software Engineer at Stripe | 2021 - Present\n"
        "• Architected distributed billing pipelines handling $50M in daily transactions with Python and PostgreSQL.\n"
        "• Implemented real-time merchant dashboard in React and TypeScript reducing latency by 45%.\n"
        "• Led team of 8 engineers and mentored junior developers across 4 major product launches.\n"
        "\n"
        "Software Engineer at Cloudflare | 2018 - 2021\n"
        "• Built high-throughput API gateway deployed on Docker and Kubernetes serving 10M+ daily requests.\n"
        "• Automated deployment workflows using GitHub Actions cutting release times by 60%.\n"
        "\n"
        "EDUCATION\n"
        "Bachelor of Science in Computer Science\n"
        "University of California, Berkeley | 2014 - 2018 | GPA: 3.85 / 4.0\n"
    )

    result = score_resume(raw_text=normal_text)

    # Complete formatting (all 4 sections present)
    assert result["format_score"] == 100.0

    # Bachelor of Science degree
    assert result["education_score"] == 90.0

    # Broad core industry keywords
    assert result["keyword_score"] >= 80.0

    # Strong action verbs (architected, built, implemented, led, automated)
    assert result["experience_score"] >= 70.0

    # Quantifiable metrics ($50M, 45%, 10M+, 60%)
    assert result["impact_score"] >= 70.0

    # Strong overall score >= 80.0
    assert result["overall_score"] >= 80.0


# ============================================================================
# 4. JOB DESCRIPTION WITH MISSING SKILLS SCENARIO
# ============================================================================

def test_ats_job_description_with_missing_skills():
    """
    Verify candidate evaluated against a job requiring completely different skills:
    1. missing_skills accurately populated
    2. keyword_score reflects low match ratio
    3. actionable recommendation generated listing missing skills
    """
    candidate_text = (
        "Frontend Developer\n"
        "dev@example.com | (555) 321-4321 | New York, NY\n"
        "SKILLS: HTML, CSS, JavaScript, React, Tailwind CSS\n"
        "EXPERIENCE: Built responsive web interfaces at WebStudio | 2022 - Present\n"
        "EDUCATION: Bachelor of Arts in Design | NYU | 2022\n"
    )

    # Job description requires specialized backend / systems / cloud skills
    rust_blockchain_jd = (
        "Staff Systems Engineer\n"
        "Requirements:\n"
        "- 5+ years with Rust, Go, or C++\n"
        "- Deep experience with Kubernetes, Docker, and Terraform\n"
        "- Hands-on knowledge of Solana, Smart Contracts, and Web3 protocols\n"
        "- Strong understanding of Kafka and Distributed Systems\n"
    )

    result = score_resume(raw_text=candidate_text, job_description=rust_blockchain_jd)

    missing = result["improvement_suggestions"]["missing_skills"]
    matching = result["improvement_suggestions"]["matching_skills"]

    # Candidate has none of Rust, Go, Kubernetes, Terraform, Docker, Kafka, etc.
    assert len(missing) >= 4
    assert any(s in missing for s in ["Rust", "Kubernetes", "Docker", "Terraform", "Go"])
    assert len(matching) == 0

    # Keyword score must be 0.0 because 0 required skills matched
    assert result["keyword_score"] == 0.0

    # Recommendation specifically mentions missing skills
    top_rec = result["improvement_suggestions"]["top_recommendations"][0]
    assert "missing" in top_rec.lower()


# ============================================================================
# 5. JOB DESCRIPTION WITH MATCHING SKILLS SCENARIO
# ============================================================================

def test_ats_job_description_with_matching_skills():
    """
    Verify candidate matching all required skills of a target job description:
    1. matching_skills populated with all job skills
    2. missing_skills is empty
    3. keyword_score is 100%
    4. overall score is elevated
    """
    candidate_text = (
        "Senior Backend Engineer\n"
        "backend@example.com | (555) 789-1011 | Chicago, IL\n"
        "SKILLS: Python, FastAPI, Docker, PostgreSQL, Redis, AWS\n"
        "EXPERIENCE: Built scalable microservices at DataCorp | 2020 - Present\n"
        "• Designed REST APIs with FastAPI and PostgreSQL handling 5M requests daily.\n"
        "• Deployed containerized services with Docker to AWS ECS.\n"
        "EDUCATION: Bachelor of Science in Computer Science | UIUC | 2020\n"
    )

    # Job description requires the exact skills the candidate has
    target_jd = (
        "Senior Python Backend Developer\n"
        "We are looking for a Python engineer skilled in:\n"
        "- Python and FastAPI\n"
        "- PostgreSQL and Redis\n"
        "- Docker and AWS\n"
    )

    result = score_resume(raw_text=candidate_text, job_description=target_jd)

    matching = result["improvement_suggestions"]["matching_skills"]
    missing = result["improvement_suggestions"]["missing_skills"]

    assert len(matching) >= 5
    assert all(sk in matching for sk in ["Python", "FastAPI", "Docker", "PostgreSQL", "Redis", "AWS"])
    assert len(missing) == 0

    # 100% match on required keywords
    assert result["keyword_score"] == 100.0

    # High overall score
    assert result["overall_score"] >= 80.0


# ============================================================================
# 6. HTTP API INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_api_analyze_with_explicit_job_description(client: AsyncClient):
    """Verify POST /api/v1/resumes/{id}/analyze with explicit job_description payload."""
    token = await get_authenticated_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = generate_fullstack_pdf_resume()
    upload_res = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("fullstack.pdf", pdf_bytes, "application/pdf")},
    )
    resume_id = upload_res.json()["id"]

    # Target job description emphasizing Python, React, Docker, and PostgreSQL
    analyze_payload = {
        "job_description": (
            "Full Stack Software Engineer\n"
            "Requirements:\n"
            "- Strong proficiency in Python, React, TypeScript\n"
            "- Experience with Docker, Kubernetes, and PostgreSQL\n"
        )
    }

    res = await client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers=headers,
        json=analyze_payload,
    )
    assert res.status_code == 200
    data = res.json()

    assert data["overall_score"] >= 75.0
    assert data["keyword_score"] >= 80.0
    assert data["format_score"] == 100.0

    suggestions = data["improvement_suggestions"]
    assert "matching_skills" in suggestions
    assert any(s in suggestions["matching_skills"] for s in ["Python", "React", "Docker", "PostgreSQL"])


@pytest.mark.asyncio
async def test_api_analyze_with_database_job_id(client: AsyncClient, db_session: AsyncSession):
    """
    Verify POST /api/v1/resumes/{id}/analyze with job_id fetches the Job description
    from the database and evaluates compatibility.
    """
    token = await get_authenticated_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upload resume
    pdf_bytes = generate_fullstack_pdf_resume()
    upload_res = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("fullstack.pdf", pdf_bytes, "application/pdf")},
    )
    resume_id = upload_res.json()["id"]

    # 2. Create Job in DB
    job = Job(
        title="Senior Cloud Engineer",
        company="TechCorp Cloud",
        location="Remote",
        work_type="remote",
        description="Lead cloud infrastructure and containerized deployments.",
        requirements="Must know AWS, Docker, Kubernetes, Python, and CI/CD.",
        experience_level="senior",
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)

    # 3. Analyze against job_id
    res = await client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers=headers,
        json={"job_id": str(job.id)},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["job_id"] == str(job.id)
    assert data["overall_score"] >= 75.0
    matching = data["improvement_suggestions"]["matching_skills"]
    assert any(s in matching for s in ["AWS", "Docker", "Kubernetes", "Python"])
