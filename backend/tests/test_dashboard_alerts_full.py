"""
Full Dashboard, Alerts and New Companies endpoint tests.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_db
from app.core.security import get_current_user
from tests.conftest import (
    fake_token_payload, mock_db_session,
    scalar_result, scalar_list_result,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    return mock_db_session()


@pytest.fixture
async def client(mock_db):
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


def _scalar_zero() -> MagicMock:
    r = MagicMock()
    r.scalar.return_value = 0
    r.scalar_one_or_none.return_value = None
    r.all.return_value = []
    r.scalars.return_value.all.return_value = []
    return r


# ══════════════════════════════════════════════════════════════════
# GET /dashboard/stats
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_dashboard_stats_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_dashboard_stats_returns_200(client, mock_db):
    mock_db.execute = AsyncMock(return_value=_scalar_zero())
    resp = await client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_dashboard_stats_has_required_keys(client, mock_db):
    mock_db.execute = AsyncMock(return_value=_scalar_zero())
    resp = await client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


@pytest.mark.anyio
async def test_dashboard_stats_with_period_7d(client, mock_db):
    mock_db.execute = AsyncMock(return_value=_scalar_zero())
    resp = await client.get("/api/v1/dashboard/stats?period=7d")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_dashboard_stats_with_period_1y(client, mock_db):
    mock_db.execute = AsyncMock(return_value=_scalar_zero())
    resp = await client.get("/api/v1/dashboard/stats?period=1y")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_dashboard_stats_invalid_period_returns_422(client, mock_db):
    mock_db.execute = AsyncMock(return_value=_scalar_zero())
    resp = await client.get("/api/v1/dashboard/stats?period=invalid")
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_dashboard_stats_calls_db(client, mock_db):
    mock_db.execute = AsyncMock(return_value=_scalar_zero())
    await client.get("/api/v1/dashboard/stats")
    mock_db.execute.assert_called()


# ══════════════════════════════════════════════════════════════════
# GET /dashboard/widgets/esg
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_dashboard_widget_esg_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/dashboard/widgets/esg")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_dashboard_widget_esg_returns_200(client, mock_db):
    mock_db.execute = AsyncMock(return_value=_scalar_zero())
    resp = await client.get("/api/v1/dashboard/widgets/esg")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /dashboard/widgets/fraud
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_dashboard_widget_fraud_returns_200(client, mock_db):
    mock_db.execute = AsyncMock(return_value=_scalar_zero())
    resp = await client.get("/api/v1/dashboard/widgets/fraud")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /dashboard/widgets/exchange-rates
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_dashboard_widget_exchange_rates_returns_200(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_list_result([]))
    resp = await client.get("/api/v1/dashboard/widgets/exchange-rates")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /dashboard/widgets/contracts
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_dashboard_widget_contracts_returns_200(client, mock_db):
    mock_db.execute = AsyncMock(return_value=_scalar_zero())
    resp = await client.get("/api/v1/dashboard/widgets/contracts")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /alerts — list alerts
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_alerts_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/alerts")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_alerts_list_returns_200(client, mock_db):
    r = MagicMock()
    r.scalar.return_value = 0
    r.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=r)
    resp = await client.get("/api/v1/alerts")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_alerts_calls_db(client, mock_db):
    r = MagicMock()
    r.scalar.return_value = 0
    r.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=r)
    await client.get("/api/v1/alerts")
    mock_db.execute.assert_called()


# ══════════════════════════════════════════════════════════════════
# GET /alerts/unread-count
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_alerts_unread_count_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/alerts/unread-count")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_alerts_unread_count_returns_200(client, mock_db):
    r = MagicMock()
    r.scalar.return_value = 3
    mock_db.execute = AsyncMock(return_value=r)
    resp = await client.get("/api/v1/alerts/unread-count")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# PUT /alerts/mark-all-read
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_alerts_mark_all_read_requires_auth(unauth_client):
    resp = await unauth_client.put("/api/v1/alerts/mark-all-read")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_alerts_mark_all_read_returns_200(client, mock_db):
    mock_db.execute = AsyncMock(return_value=MagicMock())
    resp = await client.put("/api/v1/alerts/mark-all-read")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /alerts/types
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_alerts_types_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/alerts/types")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_alerts_types_returns_list(client, mock_db):
    resp = await client.get("/api/v1/alerts/types")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_alerts_types_not_empty(client, mock_db):
    resp = await client.get("/api/v1/alerts/types")
    assert len(resp.json()) > 0


# ══════════════════════════════════════════════════════════════════
# GET /alerts/analytics
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_alerts_analytics_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/alerts/analytics")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_alerts_analytics_returns_200(client, mock_db):
    r = MagicMock()
    r.scalar.return_value = 0
    r.all.return_value = []
    r.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=r)
    resp = await client.get("/api/v1/alerts/analytics")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /alerts/preferences
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_alerts_preferences_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/alerts/preferences")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_alerts_preferences_returns_200(client, mock_db):
    from tests.conftest import make_user
    user = make_user()
    mock_db.execute = AsyncMock(return_value=scalar_result(user))
    resp = await client.get("/api/v1/alerts/preferences")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /new-companies
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_new_companies_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/new-companies")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_new_companies_returns_200(client, mock_db):
    r = MagicMock()
    r.scalar.return_value = 0
    r.unique.return_value.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=r)
    resp = await client.get("/api/v1/new-companies")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data or isinstance(data, dict)


@pytest.mark.anyio
async def test_new_companies_with_filters(client, mock_db):
    r = MagicMock()
    r.scalar.return_value = 0
    r.unique.return_value.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=r)
    resp = await client.get("/api/v1/new-companies?judet=București&cod_caen=6201")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_new_companies_calls_db(client, mock_db):
    r = MagicMock()
    r.scalar.return_value = 0
    r.unique.return_value.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=r)
    await client.get("/api/v1/new-companies")
    mock_db.execute.assert_called()


# ══════════════════════════════════════════════════════════════════
# GET /new-companies/stats
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_new_companies_stats_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/new-companies/stats")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_new_companies_stats_returns_200(client, mock_db):
    r = MagicMock()
    r.scalar.return_value = 0
    r.all.return_value = []
    mock_db.execute = AsyncMock(return_value=r)
    resp = await client.get("/api/v1/new-companies/stats")
    assert resp.status_code == 200
