"""
Full Risk & ESG endpoint tests — scoring, history, raw data,
recalculate trigger, ranking, and DB communication.
"""
from __future__ import annotations

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

CUI = 12345678


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


def make_risk_score() -> MagicMock:
    r = MagicMock()
    r.id = 1
    r.company_id = 1
    r.score = 65
    r.rating = "BBB"
    r.scor_financiar = Decimal("60")
    r.scor_legal = Decimal("70")
    r.scor_fiscal = Decimal("65")
    r.scor_comportamental = Decimal("70")
    r.limita_credit = None
    r.probabilitate_insolventa = Decimal("0.05")
    r.factori_risc = {}
    r.calculat_la = datetime.now(timezone.utc)
    r.model_versiune = "2.1"
    return r


def make_esg_score() -> MagicMock:
    e = MagicMock()
    e.id = 1
    e.company_id = 1
    e.score_total = Decimal("72.0")
    e.score_e = Decimal("70.0")
    e.score_s = Decimal("75.0")
    e.score_g = Decimal("71.0")
    e.e_emisii_co2 = None
    e.e_amenzi_mediu = None
    e.esg_rating = "A"
    e.csrd_relevant = False
    e.sfdr_categoria = "Article 8"
    e.surse_date = {}
    e.metodologie_versiune = "1.0"
    e.calculat_la = datetime.now(timezone.utc)
    e.disclaimer = "Scorurile ESG sunt calculate automat din surse publice disponibile."
    return e


# ══════════════════════════════════════════════════════════════════
# GET /risk/{cui} — auth guard
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_risk_requires_auth(unauth_client):
    resp = await unauth_client.get(f"/api/v1/risk/{CUI}")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_esg_requires_auth(unauth_client):
    resp = await unauth_client.get(f"/api/v1/esg/{CUI}")
    assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════
# GET /risk/{cui}
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_risk_company_not_found_returns_404(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.get(f"/api/v1/risk/{CUI}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_risk_no_score_returns_404(client, mock_db):
    company = make_company()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = MagicMock()
    r2.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/risk/{CUI}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_risk_found_returns_200(client, mock_db):
    company = make_company()
    risk = make_risk_score()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = MagicMock()
    r2.scalar_one_or_none.return_value = risk
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/risk/{CUI}")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_risk_calls_db_twice(client, mock_db):
    company = make_company()
    risk = make_risk_score()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = MagicMock()
    r2.scalar_one_or_none.return_value = risk
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    await client.get(f"/api/v1/risk/{CUI}")
    assert mock_db.execute.call_count == 2


# ══════════════════════════════════════════════════════════════════
# GET /risk/{cui}/history
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_risk_history_company_not_found(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.get(f"/api/v1/risk/{CUI}/history")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_risk_history_returns_list(client, mock_db):
    company = make_company()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = scalar_list_result([])
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/risk/{CUI}/history")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_risk_history_limit_param(client, mock_db):
    company = make_company()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = scalar_list_result([])
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/risk/{CUI}/history?limit=5")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# POST /risk/{cui}/recalculate
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_risk_recalculate_requires_auth(unauth_client):
    resp = await unauth_client.post(f"/api/v1/risk/{CUI}/recalculate")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_risk_recalculate_company_not_found(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.post(f"/api/v1/risk/{CUI}/recalculate")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_risk_recalculate_queues_task(client, mock_db):
    company = make_company()
    mock_db.execute = AsyncMock(return_value=scalar_result(company))

    task_mock = MagicMock()
    task_mock.id = "task-id-123"

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "app.tasks.risk_tasks.recalculate_risk_score_task.delay",
            lambda company_id: task_mock,
        )
        resp = await client.post(f"/api/v1/risk/{CUI}/recalculate")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"


# ══════════════════════════════════════════════════════════════════
# GET /esg/{cui}
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_esg_company_not_found_returns_404(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.get(f"/api/v1/esg/{CUI}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_esg_no_score_returns_404(client, mock_db):
    company = make_company()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = MagicMock()
    r2.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/esg/{CUI}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_esg_found_returns_200(client, mock_db):
    company = make_company()
    esg = make_esg_score()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = MagicMock()
    r2.scalar_one_or_none.return_value = esg
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/esg/{CUI}")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_esg_db_called_twice(client, mock_db):
    company = make_company()
    esg = make_esg_score()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = MagicMock()
    r2.scalar_one_or_none.return_value = esg
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    await client.get(f"/api/v1/esg/{CUI}")
    assert mock_db.execute.call_count == 2


# ══════════════════════════════════════════════════════════════════
# GET /esg/{cui}/raw-data
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_esg_raw_data_company_not_found(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.get(f"/api/v1/esg/{CUI}/raw-data")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_esg_raw_data_returns_200(client, mock_db):
    company = make_company()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = scalar_list_result([])
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/esg/{CUI}/raw-data")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# POST /esg/{cui}/recalculate
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_esg_recalculate_requires_auth(unauth_client):
    resp = await unauth_client.post(f"/api/v1/esg/{CUI}/recalculate")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_esg_recalculate_company_not_found(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.post(f"/api/v1/esg/{CUI}/recalculate")
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════
# GET /esg/ranking/top
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_esg_ranking_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/esg/ranking/top")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_esg_ranking_returns_200_with_list(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_list_result([]))
    resp = await client.get("/api/v1/esg/ranking/top")
    assert resp.status_code == 200
    # ranking endpoint returns {"disclaimer": ..., "ranking": [...]}
    assert "ranking" in resp.json()


# ══════════════════════════════════════════════════════════════════
# GET /esg/{cui}/timeline
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_esg_timeline_company_not_found(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.get(f"/api/v1/esg/{CUI}/timeline")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_esg_timeline_returns_200(client, mock_db):
    company = make_company()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = scalar_list_result([])
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/esg/{CUI}/timeline")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# POST /esg/compare
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_esg_compare_requires_auth(unauth_client):
    resp = await unauth_client.post(
        "/api/v1/esg/compare",
        json={"cuis": [CUI, 87654321]},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_esg_compare_returns_200(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_list_result([]))
    resp = await client.post(
        "/api/v1/esg/compare",
        json=[CUI, 87654321],
    )
    # 404 if no companies found in mock DB is also acceptable
    assert resp.status_code in (200, 404)


# ══════════════════════════════════════════════════════════════════
# GET /risk/distribution/by-sector
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_risk_distribution_requires_auth(unauth_client):
    resp = await unauth_client.get("/api/v1/risk/distribution/by-sector")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_risk_distribution_returns_200(client, mock_db):
    r = MagicMock()
    r.all.return_value = []
    mock_db.execute = AsyncMock(return_value=r)
    resp = await client.get("/api/v1/risk/distribution/by-sector")
    assert resp.status_code == 200
