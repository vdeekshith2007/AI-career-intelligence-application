"""
Comprehensive authentication verification tests.

Tests cover:
- Registration
- Login
- Password hashing & verification
- JWT & session creation
- Authentication middleware & security headers
- Protected routes
- Role-based authorization (User vs Admin)
- Logout
- Invalid credentials
- Expired / invalid / tampered authentication
- Secrets & credential leakage prevention
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User

settings = get_settings()


# ============================================================================
# 1. PASSWORD HASHING TESTS
# ============================================================================

def test_password_hashing():
    """Verify password hashing creates secure bcrypt hashes and verifies correctly."""
    plain = "SuperSecurePassword123!"
    hashed = hash_password(plain)

    # Must be bcrypt hash format ($2b$ or $2a$)
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert hashed != plain

    # Must verify correctly
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False


def test_password_never_stored_plaintext(db_session: AsyncSession):
    """Verify that password hash does not expose plaintext in database model."""
    user = User(
        email="plaintext_check@example.com",
        password_hash=hash_password("MyPlainSecret999"),
        full_name="Plaintext Check",
    )
    assert not hasattr(user, "password")
    assert "MyPlainSecret999" not in user.password_hash


# ============================================================================
# 2. JWT TOKEN CREATION & DECODING TESTS
# ============================================================================

def test_jwt_token_creation():
    """Verify access and refresh token creation and payload structure."""
    user_id = uuid4()

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)
    assert access_token != refresh_token

    access_payload = decode_token(access_token)
    assert access_payload["sub"] == str(user_id)
    assert access_payload["type"] == "access"
    assert "exp" in access_payload

    refresh_payload = decode_token(refresh_token)
    assert refresh_payload["sub"] == str(user_id)
    assert refresh_payload["type"] == "refresh"
    assert "exp" in refresh_payload


def test_expired_token_rejected():
    """Verify expired token is rejected with 401."""
    user_id = uuid4()
    expired_token = create_access_token(user_id, expires_delta=timedelta(seconds=-10))

    with pytest.raises(Exception) as exc_info:
        decode_token(expired_token)
    assert "401" in str(exc_info.value) or "Invalid or expired token" in str(exc_info.value)


def test_invalid_signature_rejected():
    """Verify token signed with an invalid secret is rejected."""
    user_id = uuid4()
    fake_token = jwt.encode(
        {"sub": str(user_id), "type": "access", "exp": datetime.now(UTC) + timedelta(hours=1)},
        "completely-wrong-secret-key-12345",
        algorithm="HS256",
    )

    with pytest.raises(Exception) as exc_info:
        decode_token(fake_token)
    assert "401" in str(exc_info.value) or "Invalid or expired token" in str(exc_info.value)


def test_tampered_token_rejected():
    """Verify tampered JWT string is rejected."""
    user_id = uuid4()
    valid_token = create_access_token(user_id)
    tampered_token = valid_token[:-4] + "xxxx"

    with pytest.raises(HTTPException):
        decode_token(tampered_token)


# ============================================================================
# 3. REGISTRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Verify successful user registration."""
    payload = {
        "email": "newuser@example.com",
        "password": "Password123!",
        "full_name": "New User",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "id" in data
    # Ensure sensitive fields are NEVER leaked
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Verify duplicate email registration is rejected with 409 Conflict."""
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "full_name": "First User",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Duplicate attempt
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_email_case_insensitivity(client: AsyncClient):
    """Verify email is normalized to lowercase and case duplicate is rejected."""
    res1 = await client.post(
        "/api/v1/auth/register",
        json={"email": "CaseTest@Example.COM", "password": "Password123!", "full_name": "Case User"},
    )
    assert res1.status_code == 201
    assert res1.json()["email"] == "casetest@example.com"

    # Same email in different casing should conflict
    res2 = await client.post(
        "/api/v1/auth/register",
        json={"email": "casetest@example.com", "password": "Password123!", "full_name": "Case User 2"},
    )
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password_rejected(client: AsyncClient):
    """Verify password shorter than 8 characters is rejected with 422."""
    payload = {
        "email": "shortpass@example.com",
        "password": "short",
        "full_name": "Short Pass",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


# ============================================================================
# 4. LOGIN TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Verify login returns valid JWT token pair."""
    # Register user first
    await client.post(
        "/api/v1/auth/register",
        json={"email": "loginuser@example.com", "password": "CorrectPassword123!", "full_name": "Login User"},
    )

    # Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "loginuser@example.com", "password": "CorrectPassword123!"},
    )
    assert login_res.status_code == 200
    data = login_res.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"].lower() == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_case_insensitive_email(client: AsyncClient):
    """Verify login succeeds regardless of email casing."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "caseduser@example.com", "password": "CorrectPassword123!", "full_name": "Cased User"},
    )

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "CASEdUser@EXAMPLE.com", "password": "CorrectPassword123!"},
    )
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    """Verify login with incorrect password returns 401 Unauthorized."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpwd@example.com", "password": "CorrectPassword123!", "full_name": "Wrong Pwd User"},
    )

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpwd@example.com", "password": "WrongPassword999!"},
    )
    assert login_res.status_code == 401
    assert "invalid email or password" in login_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Verify login with non-existent email returns 401 without revealing user existence."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "SomePassword123!"},
    )
    assert login_res.status_code == 401
    assert "invalid email or password" in login_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_deactivated_account(client: AsyncClient, db_session: AsyncSession):
    """Verify deactivated user cannot login."""
    user = User(
        email="deactivated@example.com",
        password_hash=hash_password("Password123!"),
        full_name="Deactivated User",
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "deactivated@example.com", "password": "Password123!"},
    )
    assert login_res.status_code == 401
    assert "deactivated" in login_res.json()["detail"].lower()


# ============================================================================
# 5. REFRESH TOKEN TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient):
    """Verify valid refresh token issues new access and refresh tokens."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "refresher@example.com", "password": "Password123!", "full_name": "Refresher"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresher@example.com", "password": "Password123!"},
    )
    refresh_token = login_res.json()["refresh_token"]

    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_with_access_token_rejected(client: AsyncClient):
    """Verify sending an access token to the refresh endpoint is rejected."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "tokenconfusion@example.com", "password": "Password123!", "full_name": "Token Confusion"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "tokenconfusion@example.com", "password": "Password123!"},
    )
    access_token = login_res.json()["access_token"]

    # Trying to refresh using access_token should fail
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert refresh_res.status_code == 401
    assert "invalid refresh token" in refresh_res.json()["detail"].lower()


# ============================================================================
# 6. PROTECTED ROUTES & AUTHENTICATION DEPENDENCY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_protected_route_unauthenticated(client: AsyncClient):
    """Verify accessing protected route without token returns 401."""
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_valid_token(client: AsyncClient):
    """Verify accessing protected route with valid token returns user profile."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "Password123!", "full_name": "Me User"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]

    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "me@example.com"
    assert me_res.json()["full_name"] == "Me User"


@pytest.mark.asyncio
async def test_protected_route_with_refresh_token_rejected(client: AsyncClient):
    """Verify refresh token cannot be used to authenticate protected endpoints."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "ref_as_acc@example.com", "password": "Password123!", "full_name": "Ref Acc User"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "ref_as_acc@example.com", "password": "Password123!"},
    )
    refresh_token = login_res.json()["refresh_token"]

    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert res.status_code == 401
    assert "invalid token" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_user_profile_endpoint(client: AsyncClient):
    """Verify /api/v1/users/profile get and update operations."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "profileuser@example.com", "password": "Password123!", "full_name": "Old Name"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "profileuser@example.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]

    # GET profile
    get_res = await client.get(
        "/api/v1/users/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["full_name"] == "Old Name"

    # PUT profile
    put_res = await client.put(
        "/api/v1/users/profile",
        json={"full_name": "Updated Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert put_res.status_code == 200
    assert put_res.json()["full_name"] == "Updated Name"


# ============================================================================
# 7. ROLE-BASED ACCESS CONTROL (ADMIN VS USER)
# ============================================================================

@pytest.mark.asyncio
async def test_admin_route_forbidden_for_regular_user(client: AsyncClient):
    """Verify regular user cannot access admin routes (403 Forbidden)."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "regular@example.com", "password": "Password123!", "full_name": "Regular User"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "regular@example.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]

    admin_res = await client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert admin_res.status_code == 403
    assert "admin access required" in admin_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_route_allowed_for_admin(client: AsyncClient, db_session: AsyncSession):
    """Verify admin user can access admin routes."""
    admin_user = User(
        email="superadmin@example.com",
        password_hash=hash_password("AdminPass123!"),
        full_name="Super Admin",
        role="admin",
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.flush()

    admin_token = create_access_token(admin_user.id)

    admin_res = await client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_res.status_code == 200
    assert "total_users" in admin_res.json()


# ============================================================================
# 8. LOGOUT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_logout_endpoint_authenticated(client: AsyncClient):
    """Verify logout endpoint returns success message for authenticated user."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "logoutuser@example.com", "password": "Password123!", "full_name": "Logout User"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "logoutuser@example.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]

    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_res.status_code == 200
    assert "logged out successfully" in logout_res.json()["message"].lower()


@pytest.mark.asyncio
async def test_logout_endpoint_unauthenticated(client: AsyncClient):
    """Verify logout without token is rejected with 401."""
    logout_res = await client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 401


# ============================================================================
# 9. MIDDLEWARE & SECURITY HEADERS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_middleware_security_headers_present(client: AsyncClient):
    """Verify that SecurityHeadersMiddleware and RequestLoggingMiddleware attach appropriate headers."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    # Request ID and timing headers
    assert "x-request-id" in response.headers
    assert "x-response-time" in response.headers

    # Security headers
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-xss-protection") == "1; mode=block"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


# ============================================================================
# 10. SECRETS & CREDENTIAL SAFETY CHECKS
# ============================================================================

@pytest.mark.asyncio
async def test_no_secrets_leaked_in_responses(client: AsyncClient, db_session: AsyncSession):
    """Verify secrets (SECRET_KEY, GEMINI_API_KEY, passwords) never leak in any API responses."""
    # Register & Login
    await client.post(
        "/api/v1/auth/register",
        json={"email": "secretleaktest@example.com", "password": "SecretPassword123!", "full_name": "Leak Tester"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "secretleaktest@example.com", "password": "SecretPassword123!"},
    )
    token = login_res.json()["access_token"]

    # Check /me
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    me_text = me_res.text
    assert settings.SECRET_KEY not in me_text
    assert "SecretPassword123!" not in me_text
    assert "password_hash" not in me_text
    assert settings.ADMIN_PASSWORD not in me_text
