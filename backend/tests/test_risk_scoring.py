"""
Unit tests for RiskScoringEngine — weight resolution, categorization, credit limit.

These tests exercise the *pure* / synchronous logic on the engine
without touching a real database (mock the async session).
"""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.services.risk_scoring import RiskScoringEngine, INDUSTRY_ZSCORE_ADJUSTMENTS


# ── helpers ────────────────────────────────────────────────────────


def _make_company(caen: str = "6201", has_insolvency: bool = False):
    """Return a lightweight mock Company with the fields used by the engine."""
    c = MagicMock()
    c.caen_principal = caen
    c.has_insolvency = has_insolvency
    c.stare = "ACTIVA"
    return c


def _engine(weight_overrides=None):
    """Create an engine with a dummy DB session."""
    return RiskScoringEngine(db=MagicMock(), weight_overrides=weight_overrides)


# ── Weight resolution ──────────────────────────────────────────────


def test_default_weights_for_unknown_caen():
    eng = _engine()
    company = _make_company(caen="9999")
    weights = eng._get_weights(company)
    assert weights == RiskScoringEngine.DEFAULT_WEIGHTS


def test_industry_weights_construction():
    eng = _engine()
    company = _make_company(caen="4120")
    weights = eng._get_weights(company)
    assert weights["fiscal"] == Decimal("0.35")  # construction fiscal emphasis


def test_industry_weights_it():
    eng = _engine()
    company = _make_company(caen="6209")
    weights = eng._get_weights(company)
    assert weights["financial"] == Decimal("0.40")  # IT financial emphasis


def test_custom_weights_override_everything():
    custom = {
        "financial": Decimal("0.50"),
        "legal": Decimal("0.20"),
        "fiscal": Decimal("0.20"),
        "behavioral": Decimal("0.10"),
    }
    eng = _engine(weight_overrides=custom)
    company = _make_company(caen="4120")  # would normally get construction weights
    weights = eng._get_weights(company)
    assert weights["financial"] == Decimal("0.50")


def test_weights_for_none_caen():
    eng = _engine()
    company = _make_company(caen=None)
    company.caen_principal = None
    weights = eng._get_weights(company)
    assert weights == RiskScoringEngine.DEFAULT_WEIGHTS


def test_weights_sum_to_one():
    eng = _engine()
    for caen_2, w in RiskScoringEngine.INDUSTRY_WEIGHTS.items():
        total = sum(w.values())
        assert total == Decimal("1.00"), f"Weights for CAEN {caen_2} sum to {total}"
    default_total = sum(RiskScoringEngine.DEFAULT_WEIGHTS.values())
    assert default_total == Decimal("1.00")


# ── Categorization ─────────────────────────────────────────────────


@pytest.mark.parametrize("score,expected", [
    (Decimal("95"), "A"),
    (Decimal("80"), "A"),
    (Decimal("79.99"), "B"),
    (Decimal("60"), "B"),
    (Decimal("59.99"), "C"),
    (Decimal("40"), "C"),
    (Decimal("39.99"), "D"),
    (Decimal("20"), "D"),
    (Decimal("19.99"), "E"),
    (Decimal("5"), "E"),
    (Decimal("0"), "E"),
])
def test_categorize(score, expected):
    eng = _engine()
    assert eng._categorize(score) == expected


# ── Credit limit estimation ────────────────────────────────────────


@pytest.mark.parametrize("score,revenue,expected_pct", [
    (Decimal("90"), 1_000_000, 0.25),
    (Decimal("70"), 1_000_000, 0.15),
    (Decimal("50"), 1_000_000, 0.08),
    (Decimal("30"), 1_000_000, 0.03),
    (Decimal("10"), 1_000_000, 0.00),
])
def test_credit_limit_by_category(score, revenue, expected_pct):
    eng = _engine()
    company = _make_company()
    details = {"revenue": str(revenue)}
    limit = eng._estimate_credit_limit(company, score, details)
    assert limit == int(revenue * expected_pct)


def test_credit_limit_no_revenue():
    eng = _engine()
    company = _make_company()
    assert eng._estimate_credit_limit(company, Decimal("80"), {}) is None


def test_credit_limit_zero_revenue():
    eng = _engine()
    company = _make_company()
    assert eng._estimate_credit_limit(company, Decimal("80"), {"revenue": "0"}) == 0


# ── Industry Z-Score adjustments ───────────────────────────────────


def test_zscore_adjustments_in_valid_range():
    for caen, mult in INDUSTRY_ZSCORE_ADJUSTMENTS.items():
        assert Decimal("0.5") <= mult <= Decimal("1.5"), f"CAEN {caen}: {mult} out of range"


def test_it_sector_zscore_higher():
    """IT sector should have ≥1.0 multiplier (asset-light, higher Z expected)."""
    assert INDUSTRY_ZSCORE_ADJUSTMENTS["62"] >= Decimal("1.0")


def test_finance_sector_zscore_lower():
    """Finance sector should have <1.0 multiplier (capital-intensive)."""
    assert INDUSTRY_ZSCORE_ADJUSTMENTS["64"] < Decimal("1.0")
