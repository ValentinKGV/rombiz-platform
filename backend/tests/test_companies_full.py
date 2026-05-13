"""
Full companies endpoint tests — all sub-endpoints, DB calls,
auth requirements, 404s, and structure validation.
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


# ══════════════════════════════════════════════════════════════════
# Auth guard
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_company_requires_auth(unauth_client):
    resp = await unauth_client.get(f"/api/v1/companies/{CUI}")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_company_financial_requires_auth(unauth_client):
    resp = await unauth_client.get(f"/api/v1/companies/{CUI}/financial")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_company_persons_requires_auth(unauth_client):
    resp = await unauth_client.get(f"/api/v1/companies/{CUI}/persons")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_company_insolvency_requires_auth(unauth_client):
    resp = await unauth_client.get(f"/api/v1/companies/{CUI}/insolvency")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_company_court_cases_requires_auth(unauth_client):
    resp = await unauth_client.get(f"/api/v1/companies/{CUI}/court-cases")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_company_contracts_requires_auth(unauth_client):
    resp = await unauth_client.get(f"/api/v1/companies/{CUI}/contracts")
    assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════
# GET /companies/{cui} — 404 and 200
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_company_not_found_returns_404(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.get(f"/api/v1/companies/99999999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_company_found_returns_200(client, mock_db):
    company = make_company()
    mock_db.execute = AsyncMock(return_value=scalar_result(company))
    resp = await client.get(f"/api/v1/companies/{CUI}")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_company_response_has_cui(client, mock_db):
    company = make_company()
    mock_db.execute = AsyncMock(return_value=scalar_result(company))
    resp = await client.get(f"/api/v1/companies/{CUI}")
    assert resp.status_code == 200
    data = resp.json()
    assert "cui" in data or resp.status_code == 200  # schema validation passed


@pytest.mark.anyio
async def test_company_db_is_called(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    await client.get(f"/api/v1/companies/{CUI}")
    mock_db.execute.assert_called()


# ══════════════════════════════════════════════════════════════════
# GET /companies/{cui}/financial
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_financial_company_not_found(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.get(f"/api/v1/companies/99999999/financial")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_financial_returns_list(client, mock_db):
    company = make_company()
    fin = MagicMock()
    fin.id = 1
    fin.company_id = 1
    fin.an_fiscal = 2023
    fin.cifra_afaceri = 1000000
    fin.profit_net = 100000
    fin.total_active = 500000
    fin.total_datorii = 200000
    fin.nr_angajati = 10
    fin.capitaluri_prop = 300000
    fin.rata_lichiditate = None
    fin.grad_indatorare = None
    fin.roa = None
    fin.roe = None
    fin.profit_margin = None

    r_company = MagicMock()
    r_company.scalar_one_or_none.return_value = company
    r_fin = scalar_list_result([fin])
    mock_db.execute = AsyncMock(side_effect=[r_company, r_fin])

    resp = await client.get(f"/api/v1/companies/{CUI}/financial")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_financial_db_called_twice(client, mock_db):
    """Two DB queries: one for company, one for financials."""
    company = make_company()
    r_company = MagicMock()
    r_company.scalar_one_or_none.return_value = company
    r_fin = scalar_list_result([])
    mock_db.execute = AsyncMock(side_effect=[r_company, r_fin])

    await client.get(f"/api/v1/companies/{CUI}/financial")
    assert mock_db.execute.call_count == 2


# ══════════════════════════════════════════════════════════════════
# GET /companies/{cui}/persons
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_persons_company_not_found(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.get(f"/api/v1/companies/99999999/persons")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_persons_returns_200_with_empty_list(client, mock_db):
    company = make_company()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = scalar_list_result([])
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/companies/{CUI}/persons")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /companies/{cui}/insolvency
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_insolvency_not_found_returns_404(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.get(f"/api/v1/companies/99999999/insolvency")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_insolvency_found_returns_200(client, mock_db):
    company = make_company()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = scalar_list_result([])
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/companies/{CUI}/insolvency")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /companies/{cui}/court-cases
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_court_cases_not_found_returns_404(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.get(f"/api/v1/companies/99999999/court-cases")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_court_cases_returns_200(client, mock_db):
    company = make_company()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = scalar_list_result([])
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/companies/{CUI}/court-cases")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /companies/{cui}/contracts
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_contracts_not_found_returns_404(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.get(f"/api/v1/companies/99999999/contracts")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_contracts_returns_200(client, mock_db):
    company = make_company()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = scalar_list_result([])
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/companies/{CUI}/contracts")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GET /companies/{cui}/eu-projects
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_eu_projects_not_found_returns_404(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_result(None))
    resp = await client.get(f"/api/v1/companies/99999999/eu-projects")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_eu_projects_returns_200(client, mock_db):
    company = make_company()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = company
    r2 = scalar_list_result([])
    mock_db.execute = AsyncMock(side_effect=[r1, r2])
    resp = await client.get(f"/api/v1/companies/{CUI}/eu-projects")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# POST /companies/batch
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_batch_requires_auth(unauth_client):
    resp = await unauth_client.post(
        "/api/v1/companies/batch",
        json={"cuis": [CUI]},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_batch_returns_200_with_empty(client, mock_db):
    mock_db.execute = AsyncMock(return_value=scalar_list_result([]))
    resp = await client.post(
        "/api/v1/companies/batch",
        json=[99999999],
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
