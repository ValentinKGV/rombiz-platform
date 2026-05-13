"""
Automated tests for CO2 / Carbon Emissions endpoints.

All tests run in demo mode (CO2_DATABASE_URL not configured),
so no external DB connection is required.

Covers:
  - GET /api/v1/co2/summary
  - GET /api/v1/co2/supply-chain
  - GET /api/v1/co2/years
  - Internal demo data generators
  - Data integrity (scope totals, trends, pagination-readiness)
  - Filter logic on supply chain demo data
  - Edge cases (missing params, unknown filters, boundary years)
"""
from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.api.v1.endpoints.co2 import _demo_summary, _DEMO_SUPPLY_CHAIN


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


CUI = "12345678"
YEAR = 2025


# ══════════════════════════════════════════════════════════════════
# Unit tests: _demo_summary()
# ══════════════════════════════════════════════════════════════════

class TestDemoSummaryUnit:
    """Tests for the _demo_summary() helper — no HTTP involved."""

    def test_returns_correct_year_field(self):
        result = _demo_summary(YEAR)
        assert result["year"] == YEAR

    def test_all_required_fields_present(self):
        result = _demo_summary(YEAR)
        required = [
            "year", "totalEmisii", "valoareMedieZi",
            "scope1", "scope2", "scope3Upstream", "scope3Downstream",
            "scope1MedieZi", "scope2MedieZi",
            "scope3UpstreamMedieZi", "scope3DownstreamMedieZi",
            "trends",
        ]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_total_equals_sum_of_scopes(self):
        result = _demo_summary(YEAR)
        expected = round(
            result["scope1"] + result["scope2"]
            + result["scope3Upstream"] + result["scope3Downstream"],
            2,
        )
        assert result["totalEmisii"] == expected

    def test_all_scope_values_positive(self):
        result = _demo_summary(YEAR)
        for key in ("scope1", "scope2", "scope3Upstream", "scope3Downstream"):
            assert result[key] > 0, f"{key} should be positive"

    def test_average_per_day_positive(self):
        result = _demo_summary(YEAR)
        assert result["valoareMedieZi"] > 0

    def test_trends_structure(self):
        result = _demo_summary(YEAR)
        trends = result["trends"]
        assert "scope1" in trends
        assert "scope2" in trends
        assert "scope3_upstream" in trends
        assert "scope3_downstream" in trends

    def test_trends_have_12_months(self):
        result = _demo_summary(YEAR)
        for key in ("scope1", "scope2", "scope3_upstream", "scope3_downstream"):
            assert len(result["trends"][key]) == 12, f"{key} trend should have 12 months"

    def test_trends_month_format(self):
        result = _demo_summary(YEAR)
        for entry in result["trends"]["scope1"]:
            assert entry["luna"].startswith(str(YEAR))
            assert "tone" in entry
            assert isinstance(entry["tone"], float)

    def test_deterministic_output_same_year(self):
        r1 = _demo_summary(YEAR)
        r2 = _demo_summary(YEAR)
        assert r1["totalEmisii"] == r2["totalEmisii"]
        assert r1["scope1"] == r2["scope1"]

    def test_different_years_produce_different_data(self):
        r1 = _demo_summary(2023)
        r2 = _demo_summary(2024)
        assert r1["totalEmisii"] != r2["totalEmisii"]

    @pytest.mark.parametrize("year", [2020, 2022, 2024, 2025])
    def test_multiple_years_valid(self, year):
        result = _demo_summary(year)
        assert result["year"] == year
        assert result["totalEmisii"] > 0


# ══════════════════════════════════════════════════════════════════
# Unit tests: _DEMO_SUPPLY_CHAIN data
# ══════════════════════════════════════════════════════════════════

class TestDemoSupplyChainData:
    """Tests for the static demo supply chain dataset."""

    def test_has_fifteen_entries(self):
        assert len(_DEMO_SUPPLY_CHAIN) == 15

    def test_all_entries_have_required_keys(self):
        keys = {"furnizor", "tara", "judet", "produsServiciu", "scope3Direction", "co2Footprint"}
        for item in _DEMO_SUPPLY_CHAIN:
            assert keys == set(item.keys()), f"Unexpected keys in {item}"

    def test_scope3_direction_only_valid_values(self):
        valid = {"Upstream", "Downstream"}
        for item in _DEMO_SUPPLY_CHAIN:
            assert item["scope3Direction"] in valid

    def test_all_co2_footprints_positive(self):
        for item in _DEMO_SUPPLY_CHAIN:
            assert item["co2Footprint"] > 0

    def test_has_both_upstream_and_downstream(self):
        directions = {i["scope3Direction"] for i in _DEMO_SUPPLY_CHAIN}
        assert "Upstream" in directions
        assert "Downstream" in directions

    def test_produs_serviciu_never_empty(self):
        for item in _DEMO_SUPPLY_CHAIN:
            assert item["produsServiciu"], "produsServiciu should never be empty"


# ══════════════════════════════════════════════════════════════════
# API integration tests: GET /co2/summary
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_summary_returns_200(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/summary?cui={CUI}&year={YEAR}")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_summary_response_structure(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/summary?cui={CUI}&year={YEAR}")
    data = resp.json()
    required = [
        "year", "totalEmisii", "valoareMedieZi",
        "scope1", "scope2", "scope3Upstream", "scope3Downstream",
        "trends",
    ]
    for field in required:
        assert field in data, f"Missing field in response: {field}"


@pytest.mark.anyio
async def test_summary_year_reflects_query(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/summary?cui={CUI}&year=2023")
    assert resp.json()["year"] == 2023


@pytest.mark.anyio
async def test_summary_defaults_to_current_year_when_no_year(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/summary?cui={CUI}")
    assert resp.status_code == 200
    assert resp.json()["year"] == date.today().year


@pytest.mark.anyio
async def test_summary_missing_cui_returns_422(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/summary?year={YEAR}")
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_summary_total_equals_scope_sum(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/summary?cui={CUI}&year={YEAR}")
    data = resp.json()
    expected = round(
        data["scope1"] + data["scope2"]
        + data["scope3Upstream"] + data["scope3Downstream"],
        2,
    )
    assert data["totalEmisii"] == expected


@pytest.mark.anyio
async def test_summary_deterministic_for_same_year(client: AsyncClient):
    r1 = (await client.get(f"/api/v1/co2/summary?cui={CUI}&year={YEAR}")).json()
    r2 = (await client.get(f"/api/v1/co2/summary?cui={CUI}&year={YEAR}")).json()
    assert r1["totalEmisii"] == r2["totalEmisii"]


@pytest.mark.anyio
async def test_summary_different_years_differ(client: AsyncClient):
    r2023 = (await client.get(f"/api/v1/co2/summary?cui={CUI}&year=2023")).json()
    r2024 = (await client.get(f"/api/v1/co2/summary?cui={CUI}&year=2024")).json()
    assert r2023["totalEmisii"] != r2024["totalEmisii"]


@pytest.mark.anyio
async def test_summary_trends_have_four_keys(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/summary?cui={CUI}&year={YEAR}")
    trends = resp.json()["trends"]
    assert set(trends.keys()) == {"scope1", "scope2", "scope3_upstream", "scope3_downstream"}


@pytest.mark.anyio
async def test_summary_trends_twelve_months(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/summary?cui={CUI}&year={YEAR}")
    trends = resp.json()["trends"]
    for key, entries in trends.items():
        assert len(entries) == 12, f"{key} should have 12 monthly entries"


# ══════════════════════════════════════════════════════════════════
# API integration tests: GET /co2/supply-chain
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_supply_chain_returns_200(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_supply_chain_returns_items_list(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}")
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.anyio
async def test_supply_chain_demo_has_fifteen_items(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}")
    assert len(resp.json()["items"]) == 15


@pytest.mark.anyio
async def test_supply_chain_year_reflected_in_response(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year=2023")
    assert resp.json()["year"] == 2023


@pytest.mark.anyio
async def test_supply_chain_missing_cui_returns_422(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?year={YEAR}")
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_supply_chain_item_structure(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}")
    item = resp.json()["items"][0]
    for key in ("furnizor", "tara", "judet", "produsServiciu", "scope3Direction", "co2Footprint"):
        assert key in item, f"Item missing key: {key}"


@pytest.mark.anyio
async def test_supply_chain_filter_by_furnizor(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}&furnizor=enel")
    items = resp.json()["items"]
    assert len(items) == 1
    assert "Enel" in items[0]["furnizor"]


@pytest.mark.anyio
async def test_supply_chain_filter_by_furnizor_case_insensitive(client: AsyncClient):
    resp_lower = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}&furnizor=fan+courier")
    resp_upper = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}&furnizor=FAN+COURIER")
    assert resp_lower.json()["items"] == resp_upper.json()["items"]


@pytest.mark.anyio
async def test_supply_chain_filter_by_tara_romania(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}&tara=România")
    items = resp.json()["items"]
    assert len(items) > 0
    for item in items:
        assert "România" in item["tara"]


@pytest.mark.anyio
async def test_supply_chain_filter_by_judet(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}&judet=Ilfov")
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["furnizor"] == "Fan Courier"


@pytest.mark.anyio
async def test_supply_chain_filter_by_produs(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}&produs=cloud")
    items = resp.json()["items"]
    assert len(items) == 1
    assert "Cloud" in items[0]["produsServiciu"]


@pytest.mark.anyio
async def test_supply_chain_filter_no_match_returns_empty(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}&furnizor=NONEXISTENT_XYZ_999")
    items = resp.json()["items"]
    assert items == []


@pytest.mark.anyio
async def test_supply_chain_filter_multiple_params(client: AsyncClient):
    """Combining tara + produs should narrow results."""
    resp_all = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}")
    resp_filtered = await client.get(
        f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}&tara=România&produs=energie"
    )
    assert len(resp_filtered.json()["items"]) < len(resp_all.json()["items"])


@pytest.mark.anyio
async def test_supply_chain_all_co2_footprints_positive(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}")
    for item in resp.json()["items"]:
        assert item["co2Footprint"] > 0


@pytest.mark.anyio
async def test_supply_chain_scope3_direction_valid_values(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}")
    for item in resp.json()["items"]:
        assert item["scope3Direction"] in ("Upstream", "Downstream")


# ══════════════════════════════════════════════════════════════════
# API integration tests: GET /co2/years
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_years_returns_200(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/years?cui={CUI}")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_years_response_has_years_key(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/years?cui={CUI}")
    assert "years" in resp.json()


@pytest.mark.anyio
async def test_years_returns_list(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/years?cui={CUI}")
    assert isinstance(resp.json()["years"], list)


@pytest.mark.anyio
async def test_years_demo_returns_three_years(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/years?cui={CUI}")
    years = resp.json()["years"]
    assert len(years) == 3


@pytest.mark.anyio
async def test_years_includes_current_year(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/years?cui={CUI}")
    years = resp.json()["years"]
    assert date.today().year in years


@pytest.mark.anyio
async def test_years_are_descending(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/years?cui={CUI}")
    years = resp.json()["years"]
    assert years == sorted(years, reverse=True)


@pytest.mark.anyio
async def test_years_missing_cui_returns_422(client: AsyncClient):
    resp = await client.get("/api/v1/co2/years")
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_years_all_integers(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/years?cui={CUI}")
    for y in resp.json()["years"]:
        assert isinstance(y, int)


@pytest.mark.anyio
async def test_years_range_is_recent(client: AsyncClient):
    """All demo years should be within the last 3 years."""
    resp = await client.get(f"/api/v1/co2/years?cui={CUI}")
    curr = date.today().year
    for y in resp.json()["years"]:
        assert curr - 3 <= y <= curr


# ══════════════════════════════════════════════════════════════════
# Cross-endpoint consistency tests
# ══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_years_aligns_with_summary(client: AsyncClient):
    """Each year returned by /years should produce a valid /summary response."""
    years_resp = await client.get(f"/api/v1/co2/years?cui={CUI}")
    for year in years_resp.json()["years"]:
        summary_resp = await client.get(f"/api/v1/co2/summary?cui={CUI}&year={year}")
        assert summary_resp.status_code == 200
        assert summary_resp.json()["year"] == year


@pytest.mark.anyio
async def test_years_aligns_with_supply_chain(client: AsyncClient):
    """Each year returned by /years should produce a valid /supply-chain response."""
    years_resp = await client.get(f"/api/v1/co2/years?cui={CUI}")
    for year in years_resp.json()["years"]:
        sc_resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={year}")
        assert sc_resp.status_code == 200
        assert "items" in sc_resp.json()


@pytest.mark.anyio
async def test_supply_chain_upstream_count_nonzero(client: AsyncClient):
    """Demo data must always have Upstream entries for Scope3."""
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}")
    upstream = [i for i in resp.json()["items"] if i["scope3Direction"] == "Upstream"]
    assert len(upstream) > 0


@pytest.mark.anyio
async def test_supply_chain_downstream_count_nonzero(client: AsyncClient):
    resp = await client.get(f"/api/v1/co2/supply-chain?cui={CUI}&year={YEAR}")
    downstream = [i for i in resp.json()["items"] if i["scope3Direction"] == "Downstream"]
    assert len(downstream) > 0
