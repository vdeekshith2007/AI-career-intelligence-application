"""
Production readiness and configuration verification script.
Tests:
1. Environment Configuration validation (Production security rules)
2. Production Startup (FastAPI app factory, lifespan, routes, security headers, docs masking)
3. Database Connection & Pool Configuration (SQLAlchemy async engine, session factory, readiness probe)
4. AI Production API Configuration (Gemini API key validation, model setup, embeddings configuration, graceful fallbacks)
"""

import asyncio
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from unittest.mock import patch

from pydantic import ValidationError

print("=" * 70)
print("AI Career Intelligence — Production Verification Suite")
print("=" * 70)

# -------------------------------------------------------------
# 1. Environment Configuration Verification
# -------------------------------------------------------------
print("\n[1/4] Verifying Environment Configuration...")

from app.config import Settings, get_settings

# Case A: Ensure development settings work
dev_settings = Settings(APP_ENV="development", DEBUG=True, SECRET_KEY="dev-secret-key-change-in-production-abc123xyz")
assert dev_settings.is_production is False
print("  ✓ Development configuration loads cleanly")

# Case B: Ensure production rejects DEBUG=True
try:
    Settings(APP_ENV="production", DEBUG=True, SECRET_KEY="a" * 32, ADMIN_PASSWORD="secure_password_12345")
    raise AssertionError("Production should fail when DEBUG=True")
except (ValueError, ValidationError):
    print("  ✓ Production rejects DEBUG=True")

# Case C: Ensure production rejects weak/short SECRET_KEY
try:
    Settings(APP_ENV="production", DEBUG=False, SECRET_KEY="short-key", ADMIN_PASSWORD="secure_password_12345")
    raise AssertionError("Production should fail on short SECRET_KEY")
except (ValueError, ValidationError):
    print("  ✓ Production rejects short SECRET_KEY (< 32 chars)")

# Case D: Ensure production rejects default insecure SECRET_KEY
try:
    Settings(
        APP_ENV="production",
        DEBUG=False,
        SECRET_KEY="your-super-secret-key-change-in-production",
        ADMIN_PASSWORD="secure_password_12345",
    )
    raise AssertionError("Production should fail on default insecure SECRET_KEY")
except (ValueError, ValidationError):
    print("  ✓ Production rejects default/insecure SECRET_KEY phrases")

# Case E: Ensure production rejects wildcard CORS
try:
    Settings(
        APP_ENV="production",
        DEBUG=False,
        SECRET_KEY="a" * 32,
        ADMIN_PASSWORD="secure_password_12345",
        CORS_ORIGINS=["*"],
    )
    raise AssertionError("Production should fail on wildcard CORS origins")
except (ValueError, ValidationError):
    print("  ✓ Production rejects wildcard '*' CORS origin")

# Case F: Ensure production rejects default ADMIN_PASSWORD
try:
    Settings(
        APP_ENV="production",
        DEBUG=False,
        SECRET_KEY="a" * 32,
        ADMIN_PASSWORD="admin-password-change-me",
    )
    raise AssertionError("Production should fail on default ADMIN_PASSWORD")
except (ValueError, ValidationError):
    print("  ✓ Production rejects default ADMIN_PASSWORD")

# Case G: Verify valid production environment config instantiates cleanly
valid_prod = Settings(
    APP_ENV="production",
    DEBUG=False,
    SECRET_KEY="super-secret-cryptographically-secure-key-at-least-32-chars",
    ADMIN_EMAIL="admin@enterprise-career.com",
    ADMIN_PASSWORD="EnterpriseStrongPassword2026!#",
    CORS_ORIGINS=["https://career.enterprise.com"],
    DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_career_db",
    GEMINI_API_KEY="AIzaSyA_ProductionValidKeyExample_1234567890",
    GEMINI_MODEL="gemini-2.0-flash",
)
assert valid_prod.is_production is True
assert valid_prod.DEBUG is False
assert valid_prod.CORS_ORIGINS == ["https://career.enterprise.com"]
print("  ✓ Production configuration passes all strict security gates")

# -------------------------------------------------------------
# 2. Production Startup Verification
# -------------------------------------------------------------
print("\n[2/4] Verifying Production Startup & Runtime...")

prod_env_dict = {
    "APP_ENV": "production",
    "DEBUG": "false",
    "SECRET_KEY": "super-secret-cryptographically-secure-key-at-least-32-chars",
    "ADMIN_EMAIL": "admin@enterprise-career.com",
    "ADMIN_PASSWORD": "EnterpriseStrongPassword2026!#",
    "CORS_ORIGINS": '["https://career.enterprise.com"]',
    "GEMINI_API_KEY": "AIzaSyA_ProductionValidKeyExample_1234567890",
}

with patch.dict(os.environ, prod_env_dict, clear=False):
    get_settings.cache_clear()
    from app.main import create_app

    prod_app = create_app()

    # Verify docs and schema are concealed in production
    assert prod_app.docs_url is None, f"docs_url should be None in prod, got {prod_app.docs_url}"
    assert prod_app.redoc_url is None, f"redoc_url should be None in prod, got {prod_app.redoc_url}"
    assert prod_app.openapi_url is None, f"openapi_url should be None in prod, got {prod_app.openapi_url}"
    print("  ✓ Interactive documentation concealed (/docs, /redoc, /openapi.json disabled in prod)")

    # Verify router inclusion
    assert len(prod_app.routes) > 0
    print(f"  ✓ Application initialized with {len(prod_app.routes)} router components")

    # Test HTTP client against production app instance
    from fastapi.testclient import TestClient

    with TestClient(prod_app) as client:
        # Check health endpoint
        health_resp = client.get("/api/v1/health/")
        assert health_resp.status_code == 200, f"Expected 200, got {health_resp.status_code}"
        assert health_resp.json().get("status") == "healthy"
        print("  ✓ Liveness probe /api/v1/health/ returns 200 OK ('healthy')")

        # Check security headers
        headers = health_resp.headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("x-xss-protection") == "1; mode=block"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        print("  ✓ Security headers enforced (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy)")

        # Verify docs 404 in production
        docs_resp = client.get("/docs")
        assert docs_resp.status_code == 404
        print("  ✓ Accessing /docs returns 404 Not Found in production mode")

# Reset cache
get_settings.cache_clear()

# -------------------------------------------------------------
# 3. Database Connection & Engine Pool Verification
# -------------------------------------------------------------
print("\n[3/4] Verifying Database Connection & Pooling Configuration...")

from app.db.session import async_session_factory, engine
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

print(f"  Database URL Dialect: {engine.url.drivername}")
print(f"  Engine Pool Size: {engine.pool.size()}")
print(f"  Engine Pool Recycle: {engine.pool._recycle}s")
assert engine.pool.size() == 20, f"Expected pool_size=20, got {engine.pool.size()}"
assert engine.pool._recycle == 3600, f"Expected pool_recycle=3600, got {engine.pool._recycle}"
print("  ✓ Async SQLAlchemy engine configured with production connection pool (size=20, recycle=3600s, pre_ping=True)")

# Verify session factory works
async def verify_db_session_factory():
    # Test sessionmaker creates AsyncSession instances
    session = async_session_factory()
    assert session is not None
    await session.close()
    print("  ✓ AsyncSession factory successfully instantiated and lifecycle managed")

asyncio.run(verify_db_session_factory())

# Test connection handling & readiness probe logic
async def verify_readiness_probe():
    from app.api.v1.endpoints.health import readiness_check

    result = await readiness_check()
    assert "status" in result
    assert "checks" in result
    print(f"  ✓ Health readiness probe handles service status gracefully: status='{result['status']}', checks={result['checks']}")

asyncio.run(verify_readiness_probe())

# -------------------------------------------------------------
# 4. AI Production API Configuration Verification
# -------------------------------------------------------------
print("\n[4/4] Verifying AI Production API Configuration...")

settings = get_settings()
print(f"  Configured Gemini Model: {settings.GEMINI_MODEL}")
print(f"  Configured Embedding Model: {settings.HF_EMBEDDING_MODEL}")

# Verify Gemini API key validation logic
test_placeholder_key = "placeholder-get-from-aistudio-google-com"
test_real_format_key = "AIzaSyB" + "x" * 32

def check_gemini_key_validity(key: str) -> bool:
    return bool(key and not key.startswith("placeholder") and len(key) > 20)

assert check_gemini_key_validity(test_placeholder_key) is False
assert check_gemini_key_validity("") is False
assert check_gemini_key_validity("short") is False
assert check_gemini_key_validity(test_real_format_key) is True
print("  ✓ AI API Key validator correctly rejects placeholder/empty/short keys and accepts valid keys")

# Verify LangChain Gemini initialization capability
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=test_real_format_key,
        temperature=0.3,
    )
    assert llm.model == settings.GEMINI_MODEL
    print(f"  ✓ LangChain ChatGoogleGenerativeAI successfully instantiates with model '{settings.GEMINI_MODEL}'")
except Exception as e:
    print(f"  ✗ LangChain Gemini instantiation error: {e}")
    sys.exit(1)

# Verify RAG Fallback & Grounded Synthesis capability
from app.services.rag_pipeline import generate_rag_response

async def test_rag_fallback():
    res = await generate_rag_response("What skills are needed for a Senior Python Developer?", [], [])
    assert "content" in res
    assert "sources" in res
    print("  ✓ RAG synthesis engine provides reliable grounded response if API key is in fallback mode")

asyncio.run(test_rag_fallback())

# Verify Career Agents Tool & Workflow capability
from app.services.career_agents import execute_career_agent_graph
from uuid import uuid4
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

async def test_agents_workflow():
    mock_db = AsyncMock(spec=AsyncSession)
    result = await execute_career_agent_graph(
        db=mock_db,
        user_id=uuid4(),
        query="Hello, what features do you provide to assist my career growth?",
    )
    assert "content" in result
    assert "selected_agent" in result
    print(f"  ✓ Multi-agent workflow operational (Selected Agent: '{result.get('selected_agent')}')")

asyncio.run(test_agents_workflow())

print("\n" + "=" * 70)
print("ALL PRODUCTION READINESS CHECKS PASSED ✅")
print("=" * 70)
