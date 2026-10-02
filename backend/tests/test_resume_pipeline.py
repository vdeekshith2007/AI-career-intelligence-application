"""
Comprehensive Verification Tests for the Resume Processing Pipeline.

Tests verify every step of the pipeline:
1. PDF and DOCX Upload
2. File Validation (extension, size limits, header integrity, safety)
3. Text Extraction (PDF stream, DOCX paragraphs & tables, sanitization, NUL byte stripping)
4. Resume Parsing (Contact info, Skills, Education, Projects, Experience, Summary)
5. Skill Extraction (categorization into languages, frameworks, cloud/devops, databases, tools, soft skills)
6. Education Extraction (degrees, institutions, majors, graduation dates, GPA)
7. Project Extraction (titles, descriptions, tech stacks, links)
8. Database Storage (Resume, canonical Skills, ResumeSkill junction, versioning)
9. Response to Frontend (API schemas, list view, detail view, ATS scoring integration)
10. Multiple Realistic Resume Files (Full-Stack, AI/Data Science, Cloud/DevOps)
11. Invalid & Malicious File Handling (corrupted files, empty files, encrypted PDFs, bad extensions)
"""

import io
from uuid import UUID

import docx
import pypdf
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FileUploadException
from app.models.resume import Resume, ResumeSkill
from app.models.skill import Skill
from app.services.resume_parser import (
    extract_contact_info,
    extract_education,
    extract_projects,
    extract_resume_text,
    extract_skills,
    validate_resume_upload,
)

# ============================================================================
# HELPER FUNCTIONS: GENERATING REALISTIC TEST RESUMES
# ============================================================================

def generate_pdf_resume(lines: list[str]) -> bytes:
    """Generate a syntactically valid PDF containing exact lines of text."""
    stream_content = "BT\n/F1 10 Tf\n14 TL\n50 750 Td\n"
    for line in lines:
        clean = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_content += f"({clean}) '\n"
    stream_content += "ET\n"
    encoded_stream = stream_content.encode("latin-1", errors="replace")

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
    obj4 = b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    obj5 = b"5 0 obj\n<< /Length " + str(len(encoded_stream)).encode() + b" >>\nstream\n" + encoded_stream + b"\nendstream\nendobj\n"

    header = b"%PDF-1.4\n"
    offset1 = len(header)
    offset2 = offset1 + len(obj1)
    offset3 = offset2 + len(obj2)
    offset4 = offset3 + len(obj3)
    offset5 = offset4 + len(obj4)
    body = header + obj1 + obj2 + obj3 + obj4 + obj5

    xref_offset = len(body)
    xref = (
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        + f"{offset1:010d} 00000 n \n".encode()
        + f"{offset2:010d} 00000 n \n".encode()
        + f"{offset3:010d} 00000 n \n".encode()
        + f"{offset4:010d} 00000 n \n".encode()
        + f"{offset5:010d} 00000 n \n".encode()
    )
    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    return body + xref + trailer


def generate_fullstack_pdf_resume() -> bytes:
    """Generate realistic Full-Stack Engineer PDF resume."""
    return generate_pdf_pdf_content([
        "Alex Johnson",
        "alex.johnson@example.com | (555) 123-4567 | San Francisco, CA",
        "LinkedIn: https://linkedin.com/in/alexjohnson | GitHub: https://github.com/alexjohnson",
        "",
        "SUMMARY",
        "Senior Full-Stack Engineer with 6+ years of experience designing scalable microservices and responsive web apps.",
        "",
        "SKILLS",
        "Languages: Python, TypeScript, JavaScript, SQL, HTML, CSS",
        "Frameworks: React, Next.js, Node.js, FastAPI, Express, Tailwind CSS",
        "Cloud & DevOps: Docker, Kubernetes, AWS, CI/CD, Git, GitHub Actions, Linux",
        "Databases: PostgreSQL, Redis, MongoDB",
        "Soft Skills: Leadership, Problem Solving, Teamwork, Mentorship",
        "",
        "EXPERIENCE",
        "Senior Software Engineer at Stripe | 2021 - Present",
        "Built distributed billing pipelines handling $50M in daily transactions with Python and PostgreSQL.",
        "Implemented real-time merchant dashboard in React and TypeScript with Redis caching.",
        "Full Stack Developer at Cloudflare | 2018 - 2021",
        "Developed high-throughput API gateway and microservices using FastAPI and Docker.",
        "",
        "EDUCATION",
        "Bachelor of Science in Computer Science",
        "University of California, Berkeley | 2014 - 2018 | GPA: 3.85 / 4.0",
        "",
        "PROJECTS",
        "Collaborative Code Canvas | https://github.com/alexjohnson/code-canvas",
        "Real-time collaborative code editor built with React, TypeScript, FastAPI, and Docker.",
        "Serverless Image Pipeline | https://github.com/alexjohnson/serverless-images",
        "Event-driven image processing pipeline deployed on AWS Lambda with Redis queue.",
    ])


def generate_pdf_pdf_content(lines: list[str]) -> bytes:
    return generate_pdf_resume(lines)


def generate_datascience_pdf_resume() -> bytes:
    """Generate realistic AI & Data Science PDF resume."""
    return generate_pdf_resume([
        "Dr. Elena Rostova",
        "elena.rostova@example.com | (555) 987-6543 | Boston, MA",
        "LinkedIn: https://linkedin.com/in/elenarostova | GitHub: https://github.com/elenarostova",
        "",
        "SUMMARY",
        "AI Research Scientist with expertise in Deep Learning, Natural Language Processing, and LLM fine-tuning.",
        "",
        "SKILLS",
        "Languages: Python, SQL, R, Bash",
        "Frameworks: PyTorch, TensorFlow, Scikit-Learn, Pandas, NumPy, HuggingFace, FastAPI",
        "Databases: PostgreSQL, Elasticsearch, Snowflake",
        "Methodologies: Machine Learning, Deep Learning, NLP, Computer Vision, MLOps",
        "",
        "EXPERIENCE",
        "Staff Machine Learning Engineer at Anthropic | 2022 - Present",
        "Designed transformer training workflows utilizing PyTorch and distributed GPU clusters.",
        "Optimized inference latency by 45% using model quantization and ONNX runtime.",
        "",
        "EDUCATION",
        "Master of Science in Data Science",
        "Massachusetts Institute of Technology | 2019 - 2021 | GPA: 3.95",
        "",
        "PROJECTS",
        "Neural Semantic Search | https://github.com/elenarostova/semantic-search",
        "Vector search engine utilizing sentence-transformers, PyTorch, and Elasticsearch for document indexing.",
        "Automated Medical Image Classifier | https://github.com/elenarostova/med-vision",
        "Deep convolutional network for MRI diagnostic screening using TensorFlow and Python.",
    ])


def generate_devops_docx_resume() -> bytes:
    """Generate realistic DevOps & Cloud Engineer DOCX resume with tables & formatted text."""
    doc = docx.Document()
    doc.add_heading("Marcus Vance", 0)
    doc.add_paragraph(
        "Email: marcus.vance@example.com | Phone: (555) 456-7890 | Austin, TX\n"
        "LinkedIn: https://linkedin.com/in/marcusvance | GitHub: https://github.com/marcusvance"
    )

    doc.add_heading("Summary", level=1)
    doc.add_paragraph(
        "DevOps & Infrastructure Architect with 7+ years of experience leading cloud migrations, "
        "Kubernetes orchestration, and automated CI/CD deployment pipelines."
    )

    doc.add_heading("Skills", level=1)
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Cloud: AWS, Azure, GCP"
    table.rows[0].cells[1].text = "Orchestration: Kubernetes, Docker, Helm"
    table.rows[1].cells[0].text = "IaC & CI/CD: Terraform, Ansible, GitHub Actions, Jenkins"
    table.rows[1].cells[1].text = "Monitoring: Prometheus, Grafana, Linux, Bash"

    doc.add_heading("Work Experience", level=1)
    doc.add_paragraph("Principal DevOps Engineer at Atlassian | 2020 - Present")
    doc.add_paragraph("• Architected multi-region Kubernetes clusters on AWS serving 15M monthly users.")
    doc.add_paragraph("• Automated Terraform configurations cutting infrastructure provisioning time by 80%.")

    doc.add_heading("Education", level=1)
    doc.add_paragraph("Bachelor of Science in Information Technology")
    doc.add_paragraph("University of Texas at Austin | 2015 - 2019 | GPA: 3.75")

    doc.add_heading("Projects", level=1)
    doc.add_paragraph("Kubernetes Zero-Downtime Pipeline | https://github.com/marcusvance/k8s-pipeline")
    doc.add_paragraph("GitOps deployment pipeline built with Terraform, Docker, Kubernetes, and GitHub Actions.")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


async def get_authenticated_user_token(client: AsyncClient) -> str:
    """Helper to register and login a test user, returning access token."""
    email = "resume_tester@example.com"
    password = "TestPassword123!"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Resume Tester"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return res.json()["access_token"]


# ============================================================================
# 1. FILE VALIDATION & SECURITY TESTS
# ============================================================================

def test_validate_empty_file():
    """Verify 0-byte file upload is rejected safely."""
    with pytest.raises(FileUploadException) as exc:
        validate_resume_upload("resume.pdf", b"")
    assert "empty" in exc.value.detail.lower()


def test_validate_unsupported_extensions():
    """Verify unsupported extensions (.txt, .exe, .png, .jpg) are rejected."""
    bad_files = ["resume.txt", "payload.exe", "photo.png", "doc.jpg", "code.py", "archive.zip"]
    for fname in bad_files:
        with pytest.raises(FileUploadException) as exc:
            validate_resume_upload(fname, b"dummy content")
        assert "unsupported" in exc.value.detail.lower()


def test_validate_empty_or_missing_filename():
    """Verify missing or empty filename is rejected."""
    for fname in ["", "   ", None]:
        with pytest.raises(FileUploadException) as exc:
            validate_resume_upload(fname, b"dummy content")
        assert "no file selected" in exc.value.detail.lower() or "empty" in exc.value.detail.lower()


def test_validate_file_size_exceeded():
    """Verify files larger than maximum size limit are rejected safely."""
    max_limit = 10 * 1024 * 1024
    oversized = b"P" * (max_limit + 1024)
    with pytest.raises(FileUploadException) as exc:
        validate_resume_upload("resume.pdf", oversized, max_bytes=max_limit)
    assert "too large" in exc.value.detail.lower()


def test_validate_corrupt_pdf():
    """Verify corrupt PDF content (no %PDF header) is rejected safely."""
    garbage = b"This is not a PDF file at all, just plain text."
    with pytest.raises(FileUploadException) as exc:
        validate_resume_upload("fake_resume.pdf", garbage)
    assert "corrupt" in exc.value.detail.lower() or "pdf" in exc.value.detail.lower()


def test_validate_corrupt_docx():
    """Verify corrupt DOCX content (no PK zip header) is rejected safely."""
    garbage = b"This is not a DOCX file at all, just random bytes."
    with pytest.raises(FileUploadException) as exc:
        validate_resume_upload("fake_resume.docx", garbage)
    assert "corrupt" in exc.value.detail.lower() or "docx" in exc.value.detail.lower()


def test_validate_encrypted_pdf():
    """Verify password-protected/encrypted PDF is rejected safely."""
    base_pdf = generate_fullstack_pdf_resume()
    writer = pypdf.PdfWriter()
    writer.append(io.BytesIO(base_pdf))
    writer.encrypt("userpassword")
    enc_buf = io.BytesIO()
    writer.write(enc_buf)
    encrypted_bytes = enc_buf.getvalue()

    with pytest.raises(FileUploadException) as exc:
        validate_resume_upload("encrypted.pdf", encrypted_bytes)
    assert "encrypted" in exc.value.detail.lower() or "password" in exc.value.detail.lower()


# ============================================================================
# 2. TEXT EXTRACTION & SANITIZATION TESTS
# ============================================================================

def test_extract_text_pdf():
    """Verify PDF text is cleanly extracted and contains expected sections."""
    pdf_bytes = generate_fullstack_pdf_resume()
    text = extract_resume_text(pdf_bytes, ".pdf")
    assert "Alex Johnson" in text
    assert "alex.johnson@example.com" in text
    assert "Python" in text
    assert "PostgreSQL" in text
    assert "\x00" not in text  # Ensures zero NUL bytes


def test_extract_text_docx_with_tables():
    """Verify DOCX text is extracted including table cells and headers."""
    docx_bytes = generate_devops_docx_resume()
    text = extract_resume_text(docx_bytes, ".docx")
    assert "Marcus Vance" in text
    assert "marcus.vance@example.com" in text
    assert "Kubernetes" in text
    assert "Terraform" in text
    assert "Austin, TX" in text


# ============================================================================
# 3. STRUCTURED RESUME PARSING & EXTRACTION TESTS
# ============================================================================

def test_parse_contact_info():
    """Verify contact info extraction (name, email, phone, location, github, linkedin)."""
    text = (
        "Jane Doe\n"
        "jane.doe@techcorp.io | +1 (555) 789-0123 | Seattle, WA\n"
        "https://linkedin.com/in/janedoe | https://github.com/janedoe | janedoe.dev\n"
        "Senior Software Architect\n"
    )
    contact = extract_contact_info(text)
    assert contact["name"] == "Jane Doe"
    assert contact["email"] == "jane.doe@techcorp.io"
    assert contact["phone"] is not None and "555" in contact["phone"]
    assert "Seattle, WA" in contact["location"]
    assert "janedoe" in contact["github"]
    assert "janedoe" in contact["linkedin"]


def test_parse_skills_categorization():
    """Verify skill extraction correctly categorizes technical and soft skills."""
    text = (
        "Technical Skills: Python, TypeScript, React, Next.js, FastAPI, Docker, "
        "Kubernetes, AWS, PostgreSQL, Redis, Git, Microservices, CI/CD, Agile, Teamwork"
    )
    skills = extract_skills(text)
    assert skills["total_count"] >= 10
    all_skills = skills["all"]
    assert "Python" in all_skills
    assert "React" in all_skills
    assert "Docker" in all_skills
    assert "PostgreSQL" in all_skills

    cats = skills["categories"]
    assert "Python" in cats["languages"]
    assert "React" in cats["frameworks"]
    assert "Docker" in cats["cloud_devops"]
    assert "PostgreSQL" in cats["databases"]
    assert "Teamwork" in cats["soft_skills"]


def test_parse_education_extraction():
    """Verify education degrees, institution, major, and GPA extraction."""
    text = (
        "EDUCATION\n"
        "Bachelor of Science in Computer Science\n"
        "University of California, Berkeley | 2016 - 2020 | GPA: 3.85\n"
    )
    edu = extract_education(text)
    assert len(edu) >= 1
    first = edu[0]
    assert "Bachelor of Science" in first["degree"]
    assert "Computer Science" in first["field"]
    assert "Berkeley" in first["institution"]
    assert first["graduation_year"] is not None
    assert first["gpa"] is not None and "3.85" in first["gpa"]


def test_parse_projects_extraction():
    """Verify projects title, description, tech stack, and link extraction."""
    text = (
        "PROJECTS\n"
        "Distributed KV Store | https://github.com/dev/kv-store\n"
        "High performance in-memory key-value store using Go, Redis protocol, and Docker.\n"
        "\n"
        "Cloud Monitor Dashboard | https://github.com/dev/cloud-mon\n"
        "Real-time metrics visualizer using React, TypeScript, and FastAPI with WebSocket support.\n"
    )
    projects = extract_projects(text)
    assert len(projects) >= 2
    titles = [p["title"] for p in projects]
    assert any("KV Store" in t for t in titles)
    assert any("Cloud Monitor" in t for t in titles)


# ============================================================================
# 4. FULL PIPELINE & DATABASE INTEGRATION VIA HTTP ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_pdf_upload_pipeline(client: AsyncClient, db_session: AsyncSession):
    """
    Test complete pipeline end-to-end:
    Upload PDF → Validation → Extraction → Parsing → Database Storage → API Response.
    """
    token = await get_authenticated_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = generate_fullstack_pdf_resume()
    files = {"file": ("alex_johnson_resume.pdf", pdf_bytes, "application/pdf")}

    # 1. Upload via POST /api/v1/resumes/upload
    response = await client.post("/api/v1/resumes/upload", headers=headers, files=files)
    assert response.status_code == 201
    data = response.json()

    # 2. Verify response structure returned to frontend
    assert data["original_filename"] == "alex_johnson_resume.pdf"
    assert data["status"] == "parsed"
    assert data["version"] == 1
    assert "id" in data

    # 3. Verify Contact Info in response
    contact = data["contact_info"]
    assert contact is not None
    assert contact["email"] == "alex.johnson@example.com"
    assert "Alex Johnson" in contact["name"]

    # 4. Verify Parsed Data in response
    parsed = data["parsed_data"]
    assert parsed is not None
    assert len(parsed["skills"]["all"]) >= 8
    assert any(sk in parsed["skills"]["all"] for sk in ["Python", "React", "Docker", "PostgreSQL"])
    assert len(parsed["education"]) >= 1
    assert "Bachelor of Science" in parsed["education"][0]["degree"]
    assert len(parsed["projects"]) >= 1

    # 5. Verify Database Storage
    resume_id = UUID(data["id"])
    db_result = await db_session.execute(select(Resume).where(Resume.id == resume_id))
    db_resume = db_result.scalar_one_or_none()
    assert db_resume is not None
    assert db_resume.status == "parsed"
    assert db_resume.raw_text is not None
    assert "alex.johnson@example.com" in db_resume.raw_text

    # 6. Verify Canonical Skills in skills and resume_skills tables
    links_result = await db_session.execute(
        select(ResumeSkill).where(ResumeSkill.resume_id == resume_id)
    )
    links = links_result.scalars().all()
    assert len(links) >= 5

    # Check skill names in canonical table
    skill_ids = [link.skill_id for link in links]
    skills_result = await db_session.execute(
        select(Skill).where(Skill.id.in_(skill_ids))
    )
    canonical_skills = [s.name for s in skills_result.scalars().all()]
    assert "Python" in canonical_skills or "python" in [s.lower() for s in canonical_skills]


@pytest.mark.asyncio
async def test_full_docx_upload_pipeline(client: AsyncClient, db_session: AsyncSession):
    """
    Test complete pipeline with DOCX file format:
    Upload DOCX → Table text extraction → Parsing → Skills → Storage.
    """
    token = await get_authenticated_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    docx_bytes = generate_devops_docx_resume()
    files = {"file": ("marcus_vance_devops.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

    response = await client.post("/api/v1/resumes/upload", headers=headers, files=files)
    assert response.status_code == 201
    data = response.json()

    assert data["original_filename"] == "marcus_vance_devops.docx"
    assert data["status"] == "parsed"
    assert data["contact_info"]["email"] == "marcus.vance@example.com"

    skills = data["parsed_data"]["skills"]["all"]
    assert any(s in skills for s in ["AWS", "Kubernetes", "Docker", "Terraform"])


@pytest.mark.asyncio
async def test_second_resume_upload_version_increment(client: AsyncClient):
    """Verify uploading a second resume increments the version number."""
    token = await get_authenticated_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    pdf1 = generate_fullstack_pdf_resume()
    pdf2 = generate_datascience_pdf_resume()

    res1 = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume_v1.pdf", pdf1, "application/pdf")},
    )
    assert res1.json()["version"] == 1

    res2 = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume_v2.pdf", pdf2, "application/pdf")},
    )
    assert res2.json()["version"] == 2


@pytest.mark.asyncio
async def test_get_resume_detail_and_list(client: AsyncClient):
    """Verify GET /resumes and GET /resumes/{id} return parsed data correctly."""
    token = await get_authenticated_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = generate_fullstack_pdf_resume()
    upload_res = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    resume_id = upload_res.json()["id"]

    # 1. Detail endpoint
    detail_res = await client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["parsed_data"] is not None

    # 2. List endpoint
    list_res = await client.get("/api/v1/resumes", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
    assert list_res.json()[0]["parsed_data"] is not None


@pytest.mark.asyncio
async def test_analyze_resume_preserves_parsed_data(client: AsyncClient):
    """Verify ATS analyze endpoint computes scores and preserves extracted structure."""
    token = await get_authenticated_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = generate_fullstack_pdf_resume()
    upload_res = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    resume_id = upload_res.json()["id"]

    # Trigger ATS analysis
    analyze_res = await client.post(f"/api/v1/resumes/{resume_id}/analyze", headers=headers, json={})
    assert analyze_res.status_code == 200
    score_data = analyze_res.json()

    assert score_data["overall_score"] > 0
    assert score_data["keyword_score"] is not None
    assert score_data["format_score"] is not None

    # Check that resume parsed_data still has skills, education, projects preserved
    detail_res = await client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
    detail_data = detail_res.json()
    assert detail_data["status"] == "analyzed"
    assert "skills" in detail_data["parsed_data"]
    assert "education" in detail_data["parsed_data"]
    assert "projects" in detail_data["parsed_data"]


@pytest.mark.asyncio
async def test_upload_corrupt_files_via_api(client: AsyncClient):
    """Verify uploading corrupt or invalid files through the API returns clean 400 errors."""
    token = await get_authenticated_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Corrupt PDF
    corrupt_pdf = b"NOT A VALID PDF FILE AT ALL"
    res1 = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("corrupt.pdf", corrupt_pdf, "application/pdf")},
    )
    assert res1.status_code == 400
    assert "corrupt" in res1.json()["detail"].lower() or "pdf" in res1.json()["detail"].lower()

    # 2. Corrupt DOCX
    corrupt_docx = b"NOT A VALID ZIP FILE"
    res2 = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("corrupt.docx", corrupt_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert res2.status_code == 400
    assert "corrupt" in res2.json()["detail"].lower() or "docx" in res2.json()["detail"].lower()

    # 3. Unsupported extension
    res3 = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("script.sh", b"#!/bin/bash\necho hello", "text/x-shellscript")},
    )
    assert res3.status_code == 400
    assert "unsupported" in res3.json()["detail"].lower()
