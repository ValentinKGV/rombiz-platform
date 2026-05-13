"""
Unit tests for ESGScoringEngine — SFDR classification, GRI coverage,
taxonomy data, carbon/energy constants.
"""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.services.esg_scoring import (
    ESGScoringEngine,
    CARBON_INTENSITY_FACTORS,
    ENERGY_PER_EMPLOYEE,
    TAXONOMY_ELIGIBLE_CAEN,
    TAXONOMY_ALIGNED_CAEN,
    GRI_MAPPING,
    CSRD_CHECKLIST,
)


def _engine():
    return ESGScoringEngine(db=MagicMock())


# ── SFDR classification ────────────────────────────────────────────


@pytest.mark.parametrize("score,expected", [
    (Decimal("90"), "Article 9+"),
    (Decimal("85"), "Article 9+"),
    (Decimal("80"), "Article 9"),
    (Decimal("75"), "Article 9"),
    (Decimal("65"), "Article 8+"),
    (Decimal("60"), "Article 8+"),
    (Decimal("55"), "Article 8"),
    (Decimal("50"), "Article 8"),
    (Decimal("40"), "Article 6+"),
    (Decimal("35"), "Article 6+"),
    (Decimal("20"), "Article 6"),
    (Decimal("0"), "Article 6"),
])
def test_classify_sfdr(score, expected):
    eng = _engine()
    assert eng._classify_sfdr(score) == expected


# ── GRI coverage computation ──────────────────────────────────────


def test_gri_coverage_returns_all_categories():
    eng = _engine()
    gri = eng._compute_gri_coverage()
    assert "E" in gri
    assert "S" in gri
    assert "G" in gri
    assert "coverage_pct" in gri


def test_gri_coverage_percentage_in_range():
    eng = _engine()
    gri = eng._compute_gri_coverage()
    assert 0 <= gri["coverage_pct"] <= 100


def test_gri_coverage_has_source_or_proxy():
    eng = _engine()
    gri = eng._compute_gri_coverage()
    for cat in ("E", "S", "G"):
        for code, info in gri[cat].items():
            if info["data_available"]:
                assert info["source"], f"{cat}/{code} has data but no source"
            else:
                # proxy_used can be None (truly unavailable) or a string
                pass


# ── Constants integrity ────────────────────────────────────────────


def test_carbon_intensity_all_positive():
    for caen, factor in CARBON_INTENSITY_FACTORS.items():
        assert factor > 0, f"CAEN {caen} has non-positive carbon factor"


def test_energy_per_employee_all_positive():
    for caen, factor in ENERGY_PER_EMPLOYEE.items():
        assert factor > 0, f"CAEN {caen} has non-positive energy factor"


def test_taxonomy_aligned_is_subset_of_eligible():
    for caen in TAXONOMY_ALIGNED_CAEN:
        assert caen in TAXONOMY_ELIGIBLE_CAEN, (
            f"CAEN {caen} is taxonomy-aligned but not listed as eligible"
        )


def test_csrd_checklist_has_12_items():
    assert len(CSRD_CHECKLIST) == 12


def test_esg_weights_sum_to_one():
    total = sum(ESGScoringEngine.WEIGHTS.values())
    assert total == Decimal("1.00")


# ── Carbon footprint estimation sanity ─────────────────────────────


def test_it_sector_lowest_carbon():
    """IT (CAEN 62) should have among the lowest carbon intensities."""
    it_factor = CARBON_INTENSITY_FACTORS.get("62", 0)
    # IT should be < 5 tonnes CO2 per million RON
    assert it_factor < 5


def test_oil_refining_highest_carbon():
    """Oil refining (CAEN 19) should have among the highest."""
    oil_factor = CARBON_INTENSITY_FACTORS.get("19", 0)
    assert oil_factor >= 100
