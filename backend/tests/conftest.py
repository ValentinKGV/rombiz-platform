"""
Shared pytest fixtures for all test modules.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.core.security import TokenPayload, create_access_token


# ── Helpers ───────────────────────────────────────────────────────

def fake_token_payload(role: str = "admin") -> TokenPayload:
    return TokenPayload(
        sub="aaaaaaaa-0000-4000-a000-000000000001",
        org_id="bbbbbbbb-0000-4000-a000-000000000001",
        role=role,
        exp=datetime(2099, 1, 1, tzinfo=timezone.utc),
        iat=datetime.now(timezone.utc),
        jti=str(uuid.uuid4()),
    )


def mock_db_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    return session


def scalar_result(value) -> MagicMock:
    """Mock execute() result that returns a single scalar."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar.return_value = value
    r.scalars.return_value.all.return_value = [] if value is None else [value]
    r.scalars.return_value.first.return_value = value
    r.all.return_value = [] if value is None else [value]
    return r


def scalar_list_result(items: list) -> MagicMock:
    """Mock execute() result that returns a list."""
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    r.all.return_value = items
    r.scalar.return_value = len(items)
    r.scalar_one_or_none.return_value = items[0] if items else None
    r.fetchall.return_value = items
    r.unique.return_value.scalars.return_value.all.return_value = items
    return r


# ── Widely-used mock model builders ──────────────────────────────

def make_company(cui: int = 12345678) -> MagicMock:
    c = MagicMock()
    c.id = 1
    c.cui = cui
    c.denumire = "Test SRL"
    c.forma_juridica = "SRL"
    c.stare = "ACTIVA"
    c.data_infiintare = None
    c.caen_principal = "6201"
    c.judet = "București"
    c.localitate = "Sector 1"
    c.adresa_completa = "Str. Test 1"
    c.platitor_tva = True
    c.has_insolvency = False
    c.has_litigation = False
    c.has_debts = False
    c.has_seap_contracts = True
    c.has_eu_projects = False
    c.capital_social = 1000
    c.lat = None
    c.lng = None
    c.data_quality_score = 80
    c.data_sources = {}
    c.created_at = datetime.now(timezone.utc)
    c.updated_at = datetime.now(timezone.utc)
    # Optional str fields that Pydantic validates — must be None, not MagicMock
    c.risk_rating = None
    c.j_nr = None
    c.cod_postal = None
    c.inactiv_fiscal = False
    c.tva_la_incasare = False
    c.split_tva = False
    c.has_trademarks = False
    c.ca_ultimul_an = None
    c.profit_ultimul_an = None
    c.nr_angajati = None
    # Relationships
    c.financials = []
    c.persons = []
    c.insolvency_cases = []
    c.court_cases = []
    c.public_contracts = []
    c.risk_score = None
    c.esg_score = None
    return c


def make_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.UUID("aaaaaaaa-0000-4000-a000-000000000001")
    u.org_id = uuid.UUID("bbbbbbbb-0000-4000-a000-000000000001")
    u.email = "test@example.com"
    u.first_name = "Ion"
    u.last_name = "Popescu"
    u.role = "admin"
    u.is_active = True
    u.email_verified = True
    u.credits_left = 100
    u.last_login = datetime.now(timezone.utc)
    u.created_at = datetime.now(timezone.utc)
    u.avatar_url = None
    u.alert_preferences = {}
    return u


def make_org() -> MagicMock:
    org = MagicMock()
    org.id = uuid.UUID("bbbbbbbb-0000-4000-a000-000000000001")
    org.name = "Test Org SRL"
    org.cui = "12345678"
    org.email = "org@example.com"
    org.subscription_plan = "STANDARD"
    org.subscription_status = "ACTIVE"
    return org
