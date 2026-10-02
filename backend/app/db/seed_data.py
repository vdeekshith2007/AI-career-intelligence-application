"""
Database initial seed data for AI Career Intelligence.

Seeds realistic job postings covering multiple specializations and seniority tiers
so job matching and ATS recommendation engines operate with rich data out of the box.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job

logger = logging.getLogger(__name__)

INITIAL_JOBS = [
    {
        "title": "Senior Full Stack Engineer",
        "company": "NextGen Systems",
        "location": "San Francisco, CA (Remote)",
        "work_type": "remote",
        "salary_range": "$145,000 - $185,000",
        "experience_level": "senior",
        "description": "We are seeking a Senior Full Stack Engineer to architect responsive user experiences and scalable microservices. You will lead technical design, optimize complex database queries, and drive high-reliability production deployments.",
        "requirements": "Strong proficiency in TypeScript, React, Next.js, Python, FastAPI, PostgreSQL, Docker, AWS, Git, and CI/CD pipelines. Experience designing RESTful APIs and optimizing async database queries. 5+ years building production applications.",
    },
    {
        "title": "AI / Machine Learning Engineer",
        "company": "Cognitive Cloud AI",
        "location": "New York, NY (Hybrid)",
        "work_type": "hybrid",
        "salary_range": "$160,000 - $210,000",
        "experience_level": "senior",
        "description": "Join our AI Platform team to build agentic workflows, RAG pipelines, and vector database architectures. You will deploy generative AI models, fine-tune embeddings, and evaluate multi-agent orchestration systems.",
        "requirements": "Proficiency in Python, LangChain, LangGraph, ChromaDB, Vector Databases, LLMs, Gemini/OpenAI APIs, PyTorch, Docker, Kubernetes, and REST APIs. Experience with RAG chunking and semantic search retrieval.",
    },
    {
        "title": "Backend Python Developer",
        "company": "Fintech Velocity",
        "location": "Austin, TX (Remote)",
        "work_type": "remote",
        "salary_range": "$120,000 - $155,000",
        "experience_level": "mid",
        "description": "Help us build resilient transactional payment services. You will design asynchronous APIs, manage relational data models, implement message queues, and write robust unit and integration test suites.",
        "requirements": "Proficiency in Python, FastAPI, PostgreSQL, SQLAlchemy, asyncpg, Redis, Docker, Git, REST API, Pytest, and Linux. Understanding of database indexing and concurrency.",
    },
    {
        "title": "Cloud DevOps & Infrastructure Engineer",
        "company": "Apex Cloud Global",
        "location": "Seattle, WA (Remote)",
        "work_type": "remote",
        "salary_range": "$135,000 - $175,000",
        "experience_level": "mid",
        "description": "Own our cloud deployment pipelines, container orchestration, and monitoring systems. You will build automated CI/CD workflows, manage multi-region infrastructure, and ensure zero-downtime releases.",
        "requirements": "Experience with Docker, Kubernetes, AWS, Terraform, CI/CD, GitHub Actions, Linux, Prometheus, Grafana, PostgreSQL, and Python/Bash scripting.",
    },
    {
        "title": "Frontend React / UI Engineer",
        "company": "PixelCraft Studio",
        "location": "Chicago, IL (Hybrid)",
        "work_type": "hybrid",
        "salary_range": "$105,000 - $140,000",
        "experience_level": "mid",
        "description": "Craft intuitive, accessible, and high-performance web applications using modern React and Tailwind CSS. Collaborate closely with product designers to ship delightful user interfaces.",
        "requirements": "Deep expertise in React, Next.js, TypeScript, Tailwind CSS, HTML5, CSS3, JavaScript, REST API integration, and Web Performance Optimization. 3+ years frontend experience.",
    },
    {
        "title": "Junior Software Engineer",
        "company": "StartUp Hub",
        "location": "Boston, MA (Remote)",
        "work_type": "remote",
        "salary_range": "$80,000 - $105,000",
        "experience_level": "junior",
        "description": "Exciting opportunity for an early-career engineer passionate about building web services. You will write clean code, collaborate with senior mentors, and contribute across the frontend and backend stack.",
        "requirements": "Solid foundations in Python, JavaScript, HTML, CSS, SQL, Git, and REST APIs. Degree in Computer Science, Software Engineering, or equivalent project portfolio.",
    },
    {
        "title": "Data Platform & Analytics Engineer",
        "company": "OmniData Analytics",
        "location": "Denver, CO (Remote)",
        "work_type": "remote",
        "salary_range": "$130,000 - $165,000",
        "experience_level": "mid",
        "description": "Design and maintain high-throughput analytical data pipelines. Transform raw telemetry into actionable business intelligence using modern data modeling and database warehousing.",
        "requirements": "Proficiency in SQL, PostgreSQL, Python, ETL pipelines, Data Warehousing, Docker, Git, Airflow, and Cloud Storage. Strong knowledge of schema design and performance tuning.",
    },
    {
        "title": "Lead Software Architect",
        "company": "Enterprise Scaled Solutions",
        "location": "Remote (US)",
        "work_type": "remote",
        "salary_range": "$190,000 - $240,000",
        "experience_level": "lead",
        "description": "Drive technical vision, software architecture standards, and distributed system design across multiple engineering pods. Mentor senior engineers and collaborate with executive stakeholders.",
        "requirements": "7+ years software engineering experience. Expertise in Distributed Systems, Microservices, Python, TypeScript, PostgreSQL, Cloud Architecture (AWS), Security, and Technical Leadership.",
    },
]


async def seed_jobs_if_empty(session: AsyncSession) -> int:
    """Check if jobs table is empty; if so, populate with initial listings."""
    try:
        count_res = await session.execute(select(func.count(Job.id)))
        count = count_res.scalar_one() or 0
        if count > 0:
            return 0

        now = datetime.now(timezone.utc)
        for item in INITIAL_JOBS:
            job = Job(
                title=item["title"],
                company=item["company"],
                location=item["location"],
                work_type=item["work_type"],
                salary_range=item["salary_range"],
                experience_level=item["experience_level"],
                description=item["description"],
                requirements=item["requirements"],
                is_active=True,
                posted_at=now,
            )
            session.add(job)

        await session.commit()
        logger.info(f"🌱 Seeded {len(INITIAL_JOBS)} initial active job listings into database")
        return len(INITIAL_JOBS)
    except Exception as exc:
        await session.rollback()
        logger.warning(f"⚠️ Failed to seed initial jobs (non-fatal): {exc}")
        return 0
