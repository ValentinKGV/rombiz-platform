"""
Geospatial BI — Branch 20.

Sub-modules:
  20.1  Company Heatmap           — Geographic density of companies
  20.2  Economic Zones            — Cluster companies into economic zones
  20.3  Proximity Analysis        — Find companies near coordinates
  20.4  Geodemographic Analysis   — Regional economic indicators
  20.5  County Analytics          — Per-county aggregated statistics
"""
from __future__ import annotations

import math
from typing import Optional

from sqlalchemy import select, func, and_, case, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Company, FinancialData, RiskScore
from app.core.logging import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 20.1  COMPANY HEATMAP
# ═══════════════════════════════════════════════════════════════════════

async def company_heatmap(
    db: AsyncSession,
    caen_code: Optional[str] = None,
    judet: Optional[str] = None,
) -> dict:
    """Geographic density data for companies (grouped by county)."""
    filters = [Company.stare == "ACTIVA"]
    if caen_code:
        filters.append(Company.caen_principal.like(f"{caen_code[:2]}%"))
    if judet:
        filters.append(Company.judet == judet)

    stmt = (
        select(
            Company.judet,
            func.count(Company.id).label("count"),
            func.avg(Company.lat).label("avg_lat"),
            func.avg(Company.lng).label("avg_lng"),
        )
        .where(and_(*filters))
        .group_by(Company.judet)
        .order_by(func.count(Company.id).desc())
    )
    rows = (await db.execute(stmt)).all()

    total = sum(r.count for r in rows)
    regions = []
    for r in rows:
        if r.judet:
            regions.append({
                "judet": r.judet,
                "company_count": r.count,
                "share_pct": round(r.count / total * 100, 2) if total > 0 else 0,
                "center_lat": round(float(r.avg_lat or 45.9), 4),
                "center_lng": round(float(r.avg_lng or 25.0), 4),
            })

    return {
        "total_companies": total,
        "regions": regions,
        "filters": {"caen_code": caen_code, "judet": judet},
    }


# ═══════════════════════════════════════════════════════════════════════
# 20.2  ECONOMIC ZONES
# ═══════════════════════════════════════════════════════════════════════

# Romanian development regions grouping
DEVELOPMENT_REGIONS = {
    "NORD-VEST": ["BIHOR", "BISTRITA-NASAUD", "CLUJ", "MARAMURES", "SATU MARE", "SALAJ"],
    "CENTRU": ["ALBA", "BRASOV", "COVASNA", "HARGHITA", "MURES", "SIBIU"],
    "NORD-EST": ["BACAU", "BOTOSANI", "IASI", "NEAMT", "SUCEAVA", "VASLUI"],
    "SUD-EST": ["BRAILA", "BUZAU", "CONSTANTA", "GALATI", "TULCEA", "VRANCEA"],
    "SUD-MUNTENIA": ["ARGES", "CALARASI", "DAMBOVITA", "GIURGIU", "IALOMITA", "PRAHOVA", "TELEORMAN"],
    "BUCURESTI-ILFOV": ["BUCURESTI", "ILFOV"],
    "SUD-VEST OLTENIA": ["DOLJ", "GORJ", "MEHEDINTI", "OLT", "VALCEA"],
    "VEST": ["ARAD", "CARAS-SEVERIN", "HUNEDOARA", "TIMIS"],
}


async def economic_zones(
    db: AsyncSession,
    caen_code: Optional[str] = None,
) -> dict:
    """Aggregate companies into Romanian development regions."""
    filters = [Company.stare == "ACTIVA"]
    if caen_code:
        filters.append(Company.caen_principal.like(f"{caen_code[:2]}%"))

    # Get county counts
    stmt = (
        select(Company.judet, func.count(Company.id).label("count"))
        .where(and_(*filters))
        .group_by(Company.judet)
    )
    county_counts = {r.judet: r.count for r in (await db.execute(stmt)).all() if r.judet}

    zones = []
    for region, counties in DEVELOPMENT_REGIONS.items():
        region_count = sum(county_counts.get(c, 0) for c in counties)
        zones.append({
            "region": region,
            "counties": counties,
            "company_count": region_count,
            "county_breakdown": {c: county_counts.get(c, 0) for c in counties},
        })

    zones.sort(key=lambda x: x["company_count"], reverse=True)

    return {
        "zones": zones,
        "total_companies": sum(z["company_count"] for z in zones),
        "filters": {"caen_code": caen_code},
    }


# ═══════════════════════════════════════════════════════════════════════
# 20.3  PROXIMITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

async def proximity_analysis(
    db: AsyncSession,
    lat: float,
    lng: float,
    radius_km: float = 10,
    caen_code: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """Find companies within a radius of given coordinates."""
    # Haversine approximation: ~111.12 km per degree latitude
    lat_delta = radius_km / 111.12
    lng_delta = radius_km / (111.12 * math.cos(math.radians(lat)))

    filters = [
        Company.stare == "ACTIVA",
        Company.lat.isnot(None),
        Company.lng.isnot(None),
        Company.lat.between(lat - lat_delta, lat + lat_delta),
        Company.lng.between(lng - lng_delta, lng + lng_delta),
    ]
    if caen_code:
        filters.append(Company.caen_principal.like(f"{caen_code[:2]}%"))

    stmt = (
        select(
            Company.id,
            Company.denumire,
            Company.cui,
            Company.caen_principal,
            Company.judet,
            Company.lat,
            Company.lng,
        )
        .where(and_(*filters))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    results = []
    for r in rows:
        # Approximate distance
        dist = math.sqrt(
            ((float(r.lat or 0) - lat) * 111.12) ** 2 +
            ((float(r.lng or 0) - lng) * 111.12 * math.cos(math.radians(lat))) ** 2
        )
        if dist <= radius_km:
            results.append({
                "company_id": r.id,
                "name": r.denumire,
                "cui": r.cui,
                "caen": r.caen_principal,
                "judet": r.judet,
                "lat": float(r.lat) if r.lat else None,
                "lng": float(r.lng) if r.lng else None,
                "distance_km": round(dist, 2),
            })

    results.sort(key=lambda x: x["distance_km"])

    return {
        "center": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "companies": results,
        "count": len(results),
    }


# ═══════════════════════════════════════════════════════════════════════
# 20.4  GEODEMOGRAPHIC ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

async def geodemographic_analysis(
    db: AsyncSession,
    judet: str,
) -> dict:
    """Regional economic indicators for a county."""
    latest_year = (await db.execute(
        select(func.max(FinancialData.an_fiscal))
    )).scalar()

    # Company stats
    total_companies = (await db.execute(
        select(func.count()).select_from(Company)
        .where(Company.judet == judet)
    )).scalar() or 0

    active_companies = (await db.execute(
        select(func.count()).select_from(Company)
        .where(and_(Company.judet == judet, Company.stare == "ACTIVA"))
    )).scalar() or 0

    # Financial aggregates
    fin_agg = (await db.execute(
        select(
            func.sum(FinancialData.cifra_afaceri).label("total_ca"),
            func.sum(FinancialData.profit_net).label("total_profit"),
            func.sum(FinancialData.nr_angajati).label("total_emp"),
            func.avg(FinancialData.cifra_afaceri).label("avg_ca"),
            func.avg(FinancialData.profit_margin).label("avg_margin"),
        )
        .join(Company, Company.id == FinancialData.company_id)
        .where(and_(Company.judet == judet, FinancialData.an_fiscal == latest_year))
    )).one()

    # Top CAEN sectors
    sector_stmt = (
        select(
            func.substr(Company.caen_principal, 1, 2).label("caen_2"),
            func.count(Company.id).label("count"),
        )
        .where(and_(Company.judet == judet, Company.stare == "ACTIVA"))
        .group_by(func.substr(Company.caen_principal, 1, 2))
        .order_by(func.count(Company.id).desc())
        .limit(10)
    )
    top_sectors = [
        {"caen_prefix": r.caen_2, "company_count": r.count}
        for r in (await db.execute(sector_stmt)).all()
        if r.caen_2
    ]

    # Risk distribution
    risk_dist = (await db.execute(
        select(
            RiskScore.rating,
            func.count(RiskScore.id).label("count"),
        )
        .join(Company, Company.id == RiskScore.company_id)
        .where(Company.judet == judet)
        .group_by(RiskScore.rating)
    )).all()
    risk_distribution = {r.rating: r.count for r in risk_dist}

    return {
        "judet": judet,
        "analysis_year": latest_year,
        "total_companies": total_companies,
        "active_companies": active_companies,
        "survival_rate": round(active_companies / total_companies * 100, 1) if total_companies else 0,
        "financials": {
            "total_revenue": float(fin_agg.total_ca or 0),
            "total_profit": float(fin_agg.total_profit or 0),
            "total_employees": int(fin_agg.total_emp or 0),
            "avg_revenue": round(float(fin_agg.avg_ca or 0), 2),
            "avg_profit_margin": round(float(fin_agg.avg_margin or 0), 2),
        },
        "top_sectors": top_sectors,
        "risk_distribution": risk_distribution,
    }


# ═══════════════════════════════════════════════════════════════════════
# 20.5  COUNTY ANALYTICS
# ═══════════════════════════════════════════════════════════════════════

async def county_analytics(
    db: AsyncSession,
) -> dict:
    """Aggregated per-county statistics for all counties."""
    latest_year = (await db.execute(
        select(func.max(FinancialData.an_fiscal))
    )).scalar()

    stmt = (
        select(
            Company.judet,
            func.count(Company.id).label("total"),
            func.sum(case((Company.stare == "ACTIVA", 1), else_=0)).label("active"),
        )
        .group_by(Company.judet)
        .order_by(func.count(Company.id).desc())
    )
    rows = (await db.execute(stmt)).all()

    counties = []
    for r in rows:
        if not r.judet:
            continue

        fin = (await db.execute(
            select(
                func.sum(FinancialData.cifra_afaceri).label("total_ca"),
                func.sum(FinancialData.nr_angajati).label("total_emp"),
            )
            .join(Company, Company.id == FinancialData.company_id)
            .where(and_(Company.judet == r.judet, FinancialData.an_fiscal == latest_year))
        )).one()

        counties.append({
            "judet": r.judet,
            "total_companies": r.total,
            "active_companies": int(r.active or 0),
            "total_revenue": float(fin.total_ca or 0),
            "total_employees": int(fin.total_emp or 0),
        })

    return {
        "analysis_year": latest_year,
        "counties": counties,
        "total_counties": len(counties),
    }
