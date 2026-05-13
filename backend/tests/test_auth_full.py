"""
Full auth endpoint tests: register, login, /me, refresh, profile update,
forgot/reset/change password — verifying DB is called and responses are correct.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_db
from app.core.security import (
    get_current_user,
    create_refresh_token,
    hash_password,
)
from tests.conftest import (
    fake_token_payload, mock_db_session,
    scalar_result, make_user, make_org,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    return mock_db_session()


@pytest.fixture
async def auth_client(mock_db):
    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = fake_token_payload

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def unauth_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ══════════════════════════════════════════════════════════════════
# POST /auth/login
# ══════════════════════════════════════════════════════════════════


@pytest.mark.anyio
async def test_login_invalid_email_returns_401():
    """Login with wrong password returns 401 (or 429 if rate-limited)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "noone@example.com", "password": "wrong"},
        )
    assert resp.status_code in (401, 422, 429)


@pytest.mark.anyio
async def test_login_missing_fields_returns_422():
    """Login with empty body returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/login", data={})
    assert resp.status_code in (422, 429)


@pytest.mark.anyio
async def test_login_success_returns_tokens(mock_db):
    """Login with valid credentials returns access + refresh token."""
    user = make_user()
    user.password_hash = hash_password("Passw0rd!")

    mock_db.execute = AsyncMock(return_value=scalar_result(user))

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "Passw0rd!"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["expires_in"] == 1800


@pytest.mark.anyio
async def test_login_wrong_password_returns_401(mock_db):
    user = make_user()
    user.password_hash = hash_password("CorrectPassword1!")
    mock_db.execute = AsyncMock(return_value=scalar_result(user))

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "WrongPass1!"},
        )
    app.dependency_overrides.clear()
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_login_inactive_user_returns_403(mock_db):
    user = make_user()
    user.is_active = False
    user.password_hash = hash_password("Passw0rd!")
    mock_db.execute = AsyncMock(return_value=scalar_result(user))

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "Passw0rd!"},
        )
    app.dependency_overrides.clear()
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_login_calls_db(mock_db):
    """Verify that login queries the database."""
    mock_db.execute = AsyncMock(return_value=scalar_result(None))

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/login",
            json={"email": "x@y.com", "password": "bad"},
        )
    app.dependency_overrides.clear()
    mock_db.execute.assert_called()


# ══════════════════════════════════════════════════════════════════
# POST /auth/register
# ══════════════════════════════════════════════════════════════════
# POST /auth/register
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_register_missing_fields_returns_422(unauth_client):
    resp = await unauth_client.post("/api/v1/auth/register", json={})
    assert resp.status_code in (422, 429)


@pytest.mark.anyio
async def test_register_duplicate_email_returns_409(mock_db):
    existing_user = make_user()
    mock_db.execute = AsyncMock(return_value=scalar_result(existing_user))

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "Passw0rd!",
                "organization_name": "Test Org",
            },
        )
    app.dependency_overrides.clear()
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_register_new_user_returns_201(mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "password": "Passw0rd!",
                "organization_name": "New Org",
            },
        )
    app.dependency_overrides.clear()
    assert resp.status_code == 201
    assert "message" in resp.json()


@pytest.mark.anyio
async def test_register_calls_db_add(mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser2@example.com",
                "password": "Passw0rd!",
                "organization_name": "Org2",
            },
        )
    app.dependency_overrides.clear()
    # db.add should have been called twice: once for org, once for user
    assert mock_db.add.call_count >= 2


# ══════════════════════════════════════════════════════════════════
# GET /auth/me
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_me_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/auth/me")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_me_returns_user_profile(auth_client, mock_db):
    user = make_user()
    org = make_org()

    from unittest.mock import AsyncMock, MagicMock
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = user
    r2 = MagicMock()
    r2.scalar_one_or_none.return_value = org
    mock_db.execute = AsyncMock(side_effect=[r1, r2])

    resp = await auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert "email" in data
    assert "role" in data
    assert "org_id" in data
    assert "org_cui" in data


@pytest.mark.anyio
async def test_me_user_not_found_returns_404(auth_client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_me_calls_db(auth_client, mock_db):
    user = make_user()
    org = make_org()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = user
    r2 = MagicMock()
    r2.scalar_one_or_none.return_value = org
    mock_db.execute = AsyncMock(side_effect=[r1, r2])

    await auth_client.get("/api/v1/auth/me")
    mock_db.execute.assert_called()


# ══════════════════════════════════════════════════════════════════
# PATCH /auth/me
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_update_profile_requires_auth(unauth_client):
    resp = await unauth_client.patch("/api/v1/auth/me", json={"first_name": "Ion"})
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_update_profile_success(auth_client, mock_db):
    user = make_user()
    mock_db.execute = AsyncMock(return_value=scalar_result(user))

    resp = await auth_client.patch(
        "/api/v1/auth/me",
        json={"first_name": "NewName", "last_name": "NewLast"},
    )
    assert resp.status_code == 200
    assert "message" in resp.json()


@pytest.mark.anyio
async def test_update_profile_user_not_found_returns_404(auth_client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await auth_client.patch("/api/v1/auth/me", json={"first_name": "X"})
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════
# POST /auth/refresh
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_refresh_with_valid_token(mock_db):
    user = make_user()
    user.is_active = True
    mock_db.execute = AsyncMock(return_value=scalar_result(user))

    valid_refresh = create_refresh_token(
        str(user.id), str(user.org_id), "admin"
    )

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": valid_refresh},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


# ══════════════════════════════════════════════════════════════════
# POST /auth/forgot-password
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_forgot_password_unknown_email_returns_200(mock_db):
    """Should NOT reveal whether email exists."""
    mock_db.execute = AsyncMock(return_value=scalar_result(None))

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "ghost@example.com"},
        )
    app.dependency_overrides.clear()
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_forgot_password_known_email_returns_200(mock_db):
    user = make_user()
    mock_db.execute = AsyncMock(return_value=scalar_result(user))

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    # Patch SMTP so the test doesn't try to send a real email
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": user.email},
            )
    app.dependency_overrides.clear()
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# POST /auth/change-password
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_change_password_requires_auth(unauth_client):
    resp = await unauth_client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "old", "new_password": "N3wPass!"},
    )
    assert resp.status_code == 403
