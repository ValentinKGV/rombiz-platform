"""
Full Admin and Fraud endpoint tests.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_db
from app.core.security import get_current_user
from tests.conftest import (
    fake_token_payload, mock_db_session,
    scalar_result, scalar_list_result, make_company,
)

COMPANY_ID = str(uuid.uuid4())
CUI = 12345678


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    return mock_db_session()


@pytest.fixture
async def admin_client(mock_db):
    """Client with admin role override."""
    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: fake_token_payload("admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def viewer_client(mock_db):
    """Client with viewer (non-admin) role."""
    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: fake_token_payload("viewer")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def unauth_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _zero_result() -> MagicMock:
    r = MagicMock()
    r.scalar.return_value = 0
    r.scalar_one_or_none.return_value = None
    r.scalars.return_value.all.return_value = []
    r.all.return_value = []
    r.fetchall.return_value = []
    return r


# ══════════════════════════════════════════════════════════════════
# GET /admin/dashboard — admin only
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_admin_dashboard_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/admin/dashboard")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_admin_dashboard_blocked_for_viewer(viewer_client, mock_db):
    mock_db.execute = AsyncMock(return_value=_zero_result())
    resp = await viewer_client.get("/api/v1/admin/dashboard")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_admin_dashboard_returns_200_for_admin(admin_client, mock_db):
    mock_db.execute = AsyncMock(return_value=_zero_result())
    resp = await admin_client.get("/api/v1/admin/dashboard")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_admin_dashboard_calls_db(admin_client, mock_db):
    mock_db.execute = AsyncMock(return_value=_zero_result())
    await admin_client.get("/api/v1/admin/dashboard")
    mock_db.execute.assert_called()


# ══════════════════════════════════════════════════════════════════
# GET /admin/data-sources
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_admin_data_sources_requires_admin(viewer_client, mock_db):
    mock_db.execute = AsyncMock(return_value=_zero_result())
    resp = await viewer_client.get("/api/v1/admin/data-sources")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_admin_data_sources_returns_list(admin_client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_list_result([]))
    resp = await admin_client.get("/api/v1/admin/data-sources")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ══════════════════════════════════════════════════════════════════
# GET /admin/users
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_admin_users_requires_admin(viewer_client, mock_db):
    mock_db.execute = AsyncMock(return_value=_zero_result())
    resp = await viewer_client.get("/api/v1/admin/users")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_admin_users_returns_200(admin_client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_list_result([]))
    resp = await admin_client.get("/api/v1/admin/users")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /admin/organizations
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_admin_orgs_requires_admin(viewer_client, mock_db):
    mock_db.execute = AsyncMock(return_value=_zero_result())
    resp = await viewer_client.get("/api/v1/admin/organizations")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_admin_orgs_returns_200(admin_client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_list_result([]))
    resp = await admin_client.get("/api/v1/admin/organizations")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /admin/audit-log
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_admin_audit_log_requires_admin(viewer_client, mock_db):
    mock_db.execute = AsyncMock(return_value=_zero_result())
    resp = await viewer_client.get("/api/v1/admin/audit-log")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_admin_audit_log_returns_200(admin_client, mock_db):
    r = MagicMock()
    r.scalar.return_value = 0
    r.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=r)
    resp = await admin_client.get("/api/v1/admin/audit-log")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /admin/config/feature-flags
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_feature_flags_requires_admin(viewer_client, mock_db):
    resp = await viewer_client.get("/api/v1/admin/config/feature-flags")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_feature_flags_returns_200(admin_client, mock_db):
    resp = await admin_client.get("/api/v1/admin/config/feature-flags")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


# ══════════════════════════════════════════════════════════════════
# GET /admin/db-stats
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_admin_db_stats_requires_admin(viewer_client, mock_db):
    resp = await viewer_client.get("/api/v1/admin/db-stats")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_admin_db_stats_returns_200(admin_client, mock_db):
    r = MagicMock()
    r.scalar.return_value = 0
    r.fetchall.return_value = []
    mock_db.execute = AsyncMock(return_value=r)
    resp = await admin_client.get("/api/v1/admin/db-stats")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# POST /admin/users/invite
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_invite_user_requires_admin(viewer_client, mock_db):
    resp = await viewer_client.post(
        "/api/v1/admin/users/invite",
        json={"email": "new@example.com", "role": "analyst"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_invite_user_missing_email_returns_422(admin_client, mock_db):
    resp = await admin_client.post("/api/v1/admin/users/invite", json={})
    assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════
# GET /fraud/{cui}/profile
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_fraud_profile_requires_auth(unauth_client):
    resp = await unauth_client.get(f"/api/v1/fraud/{CUI}/profile")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_fraud_profile_company_not_found(admin_client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await admin_client.get(f"/api/v1/fraud/{CUI}/profile")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_fraud_profile_returns_200(admin_client, mock_db):
    company = make_company()
    results = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=company)),  # company lookup
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # alerts
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),     # graph metrics
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # relations
    ]
    mock_db.execute = AsyncMock(side_effect=results)
    resp = await admin_client.get(f"/api/v1/fraud/{CUI}/profile")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_fraud_profile_calls_db(admin_client, mock_db):
    company = make_company()
    results = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=company)),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
    ]
    mock_db.execute = AsyncMock(side_effect=results)
    await admin_client.get(f"/api/v1/fraud/{CUI}/profile")
    assert mock_db.execute.call_count >= 2


# ══════════════════════════════════════════════════════════════════
# GET /fraud/{cui}/alerts
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_fraud_alerts_requires_auth(unauth_client):
    resp = await unauth_client.get(f"/api/v1/fraud/{CUI}/alerts")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_fraud_alerts_company_not_found(admin_client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await admin_client.get(f"/api/v1/fraud/{CUI}/alerts")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_fraud_alerts_returns_list(admin_client, mock_db):
    company = make_company()
    r1 = MagicMock(scalar_one_or_none=MagicMock(return_value=company))
    r2 = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await admin_client.get(f"/api/v1/fraud/{CUI}/alerts")
    assert resp.status_code == 200
    # endpoint returns {"disclaimer": ..., "alerts": [...]}
    assert "alerts" in resp.json()


# ══════════════════════════════════════════════════════════════════
# GET /fraud/{cui}/composite-score
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_fraud_composite_score_company_not_found(admin_client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await admin_client.get(f"/api/v1/fraud/{CUI}/composite-score")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_fraud_composite_score_returns_200(admin_client, mock_db):
    from unittest.mock import patch, AsyncMock as _AsyncMock
    company = make_company()
    r1 = MagicMock(scalar_one_or_none=MagicMock(return_value=company))
    mock_db.execute = AsyncMock(side_effect=[r1])
    mock_score = {"composite_score": 45, "risk_level": "medium"}
    with patch(
        "app.api.v1.endpoints.fraud.FraudGraphEngine.composite_fraud_score",
        new=_AsyncMock(return_value=mock_score),
    ):
        resp = await admin_client.get(f"/api/v1/fraud/{CUI}/composite-score")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /fraud/detection/algorithms
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_fraud_algorithms_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/fraud/detection/algorithms")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_fraud_algorithms_returns_list(admin_client, mock_db):
    resp = await admin_client.get("/api/v1/fraud/detection/algorithms")
    assert resp.status_code == 200
    # endpoint returns {"disclaimer": ..., "algorithms": [...]}
    assert "algorithms" in resp.json()
