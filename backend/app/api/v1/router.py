"""
Aggregated API v1 router.

All endpoint modules are registered here under their respective prefixes.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, chat, health, jobs, resumes, skills, users

api_v1_router = APIRouter()

api_v1_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)
api_v1_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)
api_v1_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)
api_v1_router.include_router(
    resumes.router,
    prefix="/resumes",
    tags=["Resumes"],
)
api_v1_router.include_router(
    jobs.router,
    prefix="/jobs",
    tags=["Jobs"],
)
api_v1_router.include_router(
    skills.router,
    prefix="/skills",
    tags=["Skills"],
)
api_v1_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat"],
)
api_v1_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"],
)
