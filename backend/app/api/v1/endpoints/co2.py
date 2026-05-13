"""
CO2 / Carbon Emissions endpoints — read-only bridge to carbon tracking database.
Provides emission data per scope, supply chain carbon intelligence, and trends.
All data is filtered by company CUI for multi-tenant isolation.

When CO2_DATABASE_URL is not configured, returns demo data.
"""
from __future__ import annotations

import random
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

router = APIRouter()

_CO2_DB_AVAILABLE = bool(settings.CO2_DATABASE_URL)


# ── Demo data generator ─────────────────────────────────────────
def _demo_summary(year: int) -> dict:
    random.seed(year)  # deterministic per year
    months = [f"{year}-{m:02d}" for m in range(1, 13)]
    s1 = [round(random.uniform(0.3, 7.5), 2) for _ in months]
    s2 = [round(random.uniform(0.4, 5.0), 2) for _ in months]
    s3u = [round(random.uniform(0.1, 4.8), 2) for _ in months]
    s3d = [round(random.uniform(0.2, 7.0), 2) for _ in months]

    total_s1 = round(sum(s1), 2)
    total_s2 = round(sum(s2), 2)
    total_s3u = round(sum(s3u), 2)
    total_s3d = round(sum(s3d), 2)
    total = round(total_s1 + total_s2 + total_s3u + total_s3d, 2)

    today = date.today()
    days = (today - date(year, 1, 1)).days or 1 if year == today.year else 365

    return {
        "year": year,
        "totalEmisii": total,
        "valoareMedieZi": round(total / days, 1),
        "scope1": total_s1,
        "scope2": total_s2,
        "scope3Upstream": total_s3u,
        "scope3Downstream": total_s3d,
        "scope1MedieZi": round(total_s1 / days, 1),
        "scope2MedieZi": round(total_s2 / days, 1),
        "scope3UpstreamMedieZi": round(total_s3u / days, 1),
        "scope3DownstreamMedieZi": round(total_s3d / days, 1),
        "trends": {
            "scope1": [{"luna": m, "tone": v} for m, v in zip(months, s1)],
            "scope2": [{"luna": m, "tone": v} for m, v in zip(months, s2)],
            "scope3_upstream": [{"luna": m, "tone": v} for m, v in zip(months, s3u)],
            "scope3_downstream": [{"luna": m, "tone": v} for m, v in zip(months, s3d)],
        },
    }


_DEMO_SUPPLY_CHAIN = [
    {"furnizor": None, "tara": None, "judet": None, "produsServiciu": "Zbor domestic - Călătorie de afaceri", "scope3Direction": "Upstream", "co2Footprint": 361.20},
    {"furnizor": None, "tara": None, "judet": None, "produsServiciu": "Zbor internațional - Europa", "scope3Direction": "Upstream", "co2Footprint": 726.97},
    {"furnizor": None, "tara": None, "judet": None, "produsServiciu": "Tren - Călătorie de afaceri", "scope3Direction": "Upstream", "co2Footprint": 27.50},
    {"furnizor": None, "tara": None, "judet": None, "produsServiciu": "Navetă angajați - Autoturism", "scope3Direction": "Upstream", "co2Footprint": 920.25},
    {"furnizor": None, "tara": None, "judet": None, "produsServiciu": "Navetă angajați - Transport public", "scope3Direction": "Upstream", "co2Footprint": 425.82},
    {"furnizor": "Enel Energie", "tara": "România", "judet": "București", "produsServiciu": "Energie electrică - grid", "scope3Direction": "Upstream", "co2Footprint": 1245.60},
    {"furnizor": "Engie România", "tara": "România", "judet": "București", "produsServiciu": "Gaz natural - încălzire", "scope3Direction": "Upstream", "co2Footprint": 890.30},
    {"furnizor": "Fan Courier", "tara": "România", "judet": "Ilfov", "produsServiciu": "Livrare colete - național", "scope3Direction": "Downstream", "co2Footprint": 312.45},
    {"furnizor": "DHL Express", "tara": "Germania", "judet": None, "produsServiciu": "Livrare internațională - curier", "scope3Direction": "Downstream", "co2Footprint": 567.80},
    {"furnizor": "Auchan", "tara": "România", "judet": "București", "produsServiciu": "Consumabile birou", "scope3Direction": "Upstream", "co2Footprint": 45.10},
    {"furnizor": "Dell Technologies", "tara": "Irlanda", "judet": None, "produsServiciu": "Echipamente IT - laptopuri", "scope3Direction": "Upstream", "co2Footprint": 1580.00},
    {"furnizor": "Amazon Web Services", "tara": "SUA", "judet": None, "produsServiciu": "Cloud hosting - servere", "scope3Direction": "Upstream", "co2Footprint": 2340.15},
    {"furnizor": None, "tara": None, "judet": None, "produsServiciu": "Deșeuri - reciclare hârtie", "scope3Direction": "Downstream", "co2Footprint": 18.90},
    {"furnizor": None, "tara": None, "judet": None, "produsServiciu": "Deșeuri - DEEE (electronice)", "scope3Direction": "Downstream", "co2Footprint": 95.40},
    {"furnizor": "OMV Petrom", "tara": "România", "judet": "Prahova", "produsServiciu": "Combustibil flotă auto", "scope3Direction": "Upstream", "co2Footprint": 1890.75},
]


# ── Endpoints ─────────────────────────────────────────────────────

@router.get("/summary")
async def co2_summary(
    cui: str = Query(..., description="CUI of the company"),
    year: int = Query(None, description="Filter year (defaults to current)"),
):
    """Total emissions + per-scope breakdown for a given company CUI."""
    year_filter = year or date.today().year

    if not _CO2_DB_AVAILABLE:
        return _demo_summary(year_filter)

    # Real DB path
    from app.core.database import get_co2_db
    from contextlib import asynccontextmanager

    async for db in get_co2_db():
        total_sql = text("""
            SELECT COALESCE(SUM(co2_tons), 0)
            FROM emissions
            WHERE cui = :cui AND EXTRACT(YEAR FROM data_raportare) = :year
        """)
        total_row = await db.execute(total_sql, {"cui": cui, "year": year_filter})
        total_emisii = float(total_row.scalar() or 0)

        scope_sql = text("""
            SELECT scope, COALESCE(SUM(co2_tons), 0)
            FROM emissions
            WHERE cui = :cui AND EXTRACT(YEAR FROM data_raportare) = :year
            GROUP BY scope
        """)
        scope_rows = await db.execute(scope_sql, {"cui": cui, "year": year_filter})
        scopes = {row[0]: float(row[1]) for row in scope_rows.fetchall()}

        trend_sql = text("""
            SELECT scope, TO_CHAR(data_raportare, 'YYYY-MM') as luna, COALESCE(SUM(co2_tons), 0)
            FROM emissions
            WHERE cui = :cui AND EXTRACT(YEAR FROM data_raportare) = :year
            GROUP BY scope, luna
            ORDER BY luna
        """)
        trend_rows = await db.execute(trend_sql, {"cui": cui, "year": year_filter})
        trends: dict[str, list] = {}
        for row in trend_rows.fetchall():
            scope_key = row[0]
            if scope_key not in trends:
                trends[scope_key] = []
            trends[scope_key].append({"luna": row[1], "tone": float(row[2])})

        today = date.today()
        days = (today - date(year_filter, 1, 1)).days or 1 if year_filter == today.year else 365

        return {
            "year": year_filter,
            "totalEmisii": round(total_emisii, 2),
            "valoareMedieZi": round(total_emisii / days, 1),
            "scope1": round(scopes.get("scope1", 0), 2),
            "scope2": round(scopes.get("scope2", 0), 2),
            "scope3Upstream": round(scopes.get("scope3_upstream", 0), 2),
            "scope3Downstream": round(scopes.get("scope3_downstream", 0), 2),
            "scope1MedieZi": round(scopes.get("scope1", 0) / days, 1),
            "scope2MedieZi": round(scopes.get("scope2", 0) / days, 1),
            "scope3UpstreamMedieZi": round(scopes.get("scope3_upstream", 0) / days, 1),
            "scope3DownstreamMedieZi": round(scopes.get("scope3_downstream", 0) / days, 1),
            "trends": trends,
        }


@router.get("/supply-chain")
async def co2_supply_chain(
    cui: str = Query(..., description="CUI of the company"),
    year: int = Query(None, description="Filter year"),
    furnizor: str = Query(None, description="Filter by supplier name"),
    tara: str = Query(None, description="Filter by country"),
    judet: str = Query(None, description="Filter by county"),
    produs: str = Query(None, description="Filter by product/service"),
):
    """Supply Chain Carbon Intelligence table."""
    year_filter = year or date.today().year

    if not _CO2_DB_AVAILABLE:
        items = _DEMO_SUPPLY_CHAIN
        # Apply client-side filters on demo data
        if furnizor:
            items = [i for i in items if i["furnizor"] and furnizor.lower() in i["furnizor"].lower()]
        if tara:
            items = [i for i in items if i["tara"] and tara.lower() in i["tara"].lower()]
        if judet:
            items = [i for i in items if i["judet"] and judet.lower() in i["judet"].lower()]
        if produs:
            items = [i for i in items if i["produsServiciu"] and produs.lower() in i["produsServiciu"].lower()]
        return {"year": year_filter, "items": items}

    # Real DB path
    from app.core.database import get_co2_db

    async for db in get_co2_db():
        conditions = ["sc.cui = :cui", "EXTRACT(YEAR FROM sc.data_raportare) = :year"]
        params: dict = {"cui": cui, "year": year_filter}

        if furnizor:
            conditions.append("LOWER(sc.furnizor) LIKE :furnizor")
            params["furnizor"] = f"%{furnizor.lower()}%"
        if tara:
            conditions.append("LOWER(sc.tara) LIKE :tara")
            params["tara"] = f"%{tara.lower()}%"
        if judet:
            conditions.append("LOWER(sc.judet) LIKE :judet")
            params["judet"] = f"%{judet.lower()}%"
        if produs:
            conditions.append("LOWER(sc.produs_serviciu) LIKE :produs")
            params["produs"] = f"%{produs.lower()}%"

        where_clause = " AND ".join(conditions)

        sql = text(f"""
            SELECT sc.furnizor, sc.tara, sc.judet,
                   sc.produs_serviciu, sc.scope3_direction,
                   COALESCE(SUM(sc.co2_tons), 0) as co2_footprint
            FROM supply_chain_emissions sc
            WHERE {where_clause}
            GROUP BY sc.furnizor, sc.tara, sc.judet, sc.produs_serviciu, sc.scope3_direction
            ORDER BY co2_footprint DESC
            LIMIT 100
        """)

        rows = await db.execute(sql, params)
        items = []
        for r in rows.fetchall():
            items.append({
                "furnizor": r[0],
                "tara": r[1],
                "judet": r[2],
                "produsServiciu": r[3],
                "scope3Direction": r[4],
                "co2Footprint": round(float(r[5]), 2),
            })

        return {"year": year_filter, "items": items}


@router.get("/years")
async def co2_available_years(
    cui: str = Query(..., description="CUI of the company"),
):
    """Return list of years that have emission data for this CUI."""
    if not _CO2_DB_AVAILABLE:
        current_year = date.today().year
        return {"years": [current_year, current_year - 1, current_year - 2]}

    from app.core.database import get_co2_db

    async for db in get_co2_db():
        sql = text("""
            SELECT DISTINCT EXTRACT(YEAR FROM data_raportare)::int as yr
            FROM emissions
            WHERE cui = :cui
            ORDER BY yr DESC
        """)
        rows = await db.execute(sql, {"cui": cui})
        return {"years": [r[0] for r in rows.fetchall()]}
