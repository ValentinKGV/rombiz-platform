"""
API integration tests — health, auth flow, company endpoints.

Uses httpx AsyncClient with ASGI transport; no real database needed
since we override the get_db and get_current_user dependencies.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.core.security import create_access_token, TokenPayload
from app.main import app
from app.core.database import get_db
from app.core.security import get_current_user


# ── Fixtures ──────────────────────────────────────────────────────


def _fake_user() -> TokenPayload:
    """Create a deterministic test user payload."""
    return TokenPayload(
        sub="test-user-id",
        org_id="test-org-id",
        role="admin",
        exp=datetime(2099, 1, 1, tzinfo=timezone.utc),
        iat=datetime.now(timezone.utc),
        jti=str(uuid.uuid4()),
    )


@pytest.fixture
def mock_db():
    """Mock async DB session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def auth_headers():
    """Valid JWT Bearer headers for protected endpoints."""
    token = create_access_token("test-user-id", "test-org-id", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client(mock_db):
    """Async test client with DI overrides."""
    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _fake_user()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def unauth_client():
    """Client WITHOUT auth override — for testing auth rejection."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Health / Root ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_health_returns_200(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.anyio
async def test_root_returns_app_name(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "app" in resp.json()


# ── Auth required ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_company_endpoint_requires_auth(unauth_client: AsyncClient):
    """Accessing protected endpoints without token should fail with 403."""
    resp = await unauth_client.get("/api/v1/companies/123456")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_login_invalid_credentials(unauth_client: AsyncClient):
    resp = await unauth_client.post(
        "/api/v1/auth/login",
        json={"email": "bad@example.com", "password": "wrong"},
    )
    assert resp.status_code in (401, 422)


# ── Company endpoints (with mock DB) ──────────────────────────────


@pytest.mark.anyio
async def test_company_not_found(client: AsyncClient, mock_db):
    """GET /companies/{cui} with no matching company should return 404."""
    # Configure mock to return no result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    resp = await client.get("/api/v1/companies/99999999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_company_financials_not_found(client: AsyncClient, mock_db):
    """GET /companies/{cui}/financial when company doesn't exist."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    resp = await client.get("/api/v1/companies/99999999/financial")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_company_persons_not_found(client: AsyncClient, mock_db):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    resp = await client.get("/api/v1/companies/99999999/persons")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_company_insolvency_not_found(client: AsyncClient, mock_db):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    resp = await client.get("/api/v1/companies/99999999/insolvency")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_company_court_cases_not_found(client: AsyncClient, mock_db):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    resp = await client.get("/api/v1/companies/99999999/court-cases")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_company_contracts_not_found(client: AsyncClient, mock_db):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    resp = await client.get("/api/v1/companies/99999999/contracts")
    assert resp.status_code == 404


# ── Reports endpoints ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_exports_list_empty(client: AsyncClient, mock_db):
    """GET /reports/exports should return an empty list when no exports exist."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    resp = await client.get("/api/v1/reports/exports")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_export_download_not_found(client: AsyncClient, mock_db):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    resp = await client.get("/api/v1/reports/exports/9999/download")
    assert resp.status_code == 404
