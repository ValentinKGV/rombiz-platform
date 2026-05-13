"""
Market Intelligence — Branch 16.

Sub-modules:
  16.1  Competitive Analysis     — Compare company against direct competitors
  16.2  Sector Benchmarks        — Industry-level performance benchmarks
  16.3  Market Sizing            — Estimate addressable market by CAEN
  16.4  M&A Target Screening     — Find acquisition-worthy companies
  16.5  Price Intelligence       — Revenue-per-employee / margin analytics
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company, FinancialData, RiskScore, ESGScore,
    CompanyPerson, PublicContract,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 16.1  COMPETITIVE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

async def competitive_analysis(
    db: AsyncSession,
    company_id: int,
    limit: int = 10,
) -> dict:
    """Find and rank direct competitors by CAEN + county."""
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită"}

    caen = company.caen_principal or ""
    caen_2 = caen[:2]

    # Latest year for the company
    latest_fin = (await db.execute(
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.desc())
        .limit(1)
    )).scalar_one_or_none()

    year = latest_fin.an_fiscal if latest_fin else date.today().year - 1

    # Find companies with the same 2-digit CAEN, same county, active
    stmt = (
        select(
            Company.id,
            Company.denumire,
            Company.cui,
            Company.caen_principal,
            Company.judet,
            FinancialData.cifra_afaceri,
            FinancialData.profit_net,
            FinancialData.nr_angajati,
            FinancialData.profit_margin,
        )
        .join(FinancialData, FinancialData.company_id == Company.id)
        .where(
            and_(
                Company.caen_principal.like(f"{caen_2}%"),
                Company.stare == "ACTIVA",
                FinancialData.an_fiscal == year,
                Company.id != company_id,
            )
        )
        .order_by(FinancialData.cifra_afaceri.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    competitors = []
    for r in rows:
        competitors.append({
            "company_id": r.id,
            "name": r.denumire,
            "cui": r.cui,
            "caen": r.caen_principal,
            "judet": r.judet,
            "cifra_afaceri": float(r.cifra_afaceri or 0),
            "profit_net": float(r.profit_net or 0),
            "nr_angajati": r.nr_angajati or 0,
            "profit_margin": round(float(r.profit_margin or 0), 2),
        })

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "caen": company.caen_principal,
        "analysis_year": year,
        "company_ca": float(latest_fin.cifra_afaceri or 0) if latest_fin else None,
        "competitors": competitors,
        "competitor_count": len(competitors),
    }


# ═══════════════════════════════════════════════════════════════════════
# 16.2  SECTOR BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════

async def sector_benchmarks(
    db: AsyncSession,
    caen_code: str,
) -> dict:
    """Industry-level financial benchmarks for a CAEN sector."""
    caen_2 = caen_code[:2]

    years_stmt = (
        select(FinancialData.an_fiscal)
        .join(Company, Company.id == FinancialData.company_id)
        .where(Company.caen_principal.like(f"{caen_2}%"))
        .distinct()
        .order_by(FinancialData.an_fiscal.desc())
        .limit(5)
    )
    years = [r for r in (await db.execute(years_stmt)).scalars().all()]

    benchmarks = []
    for yr in years:
        stats = (await db.execute(
            select(
                func.count(FinancialData.id).label("n"),
                func.avg(FinancialData.cifra_afaceri).label("avg_ca"),
                func.avg(FinancialData.profit_net).label("avg_profit"),
                func.avg(FinancialData.nr_angajati).label("avg_emp"),
                func.avg(FinancialData.rata_lichiditate).label("avg_lichid"),
                func.avg(FinancialData.grad_indatorare).label("avg_debt"),
                func.avg(FinancialData.roa).label("avg_roa"),
                func.avg(FinancialData.roe).label("avg_roe"),
                func.avg(FinancialData.profit_margin).label("avg_margin"),
                func.sum(FinancialData.cifra_afaceri).label("total_ca"),
                func.sum(FinancialData.nr_angajati).label("total_emp"),
            )
            .join(Company, Company.id == FinancialData.company_id)
            .where(and_(Company.caen_principal.like(f"{caen_2}%"), FinancialData.an_fiscal == yr))
        )).one()

        benchmarks.append({
            "year": yr,
            "company_count": stats.n,
            "avg_cifra_afaceri": round(float(stats.avg_ca or 0), 2),
            "avg_profit_net": round(float(stats.avg_profit or 0), 2),
            "avg_nr_angajati": round(float(stats.avg_emp or 0), 1),
            "avg_lichiditate": round(float(stats.avg_lichid or 0), 2),
            "avg_grad_indatorare": round(float(stats.avg_debt or 0), 2),
            "avg_roa": round(float(stats.avg_roa or 0), 2),
            "avg_roe": round(float(stats.avg_roe or 0), 2),
            "avg_profit_margin": round(float(stats.avg_margin or 0), 2),
            "total_ca_sector": float(stats.total_ca or 0),
            "total_angajati": int(stats.total_emp or 0),
        })

    return {
        "caen_code": caen_code,
        "caen_prefix": caen_2,
        "benchmarks": benchmarks,
    }


# ═══════════════════════════════════════════════════════════════════════
# 16.3  MARKET SIZING
# ═══════════════════════════════════════════════════════════════════════

async def market_sizing(
    db: AsyncSession,
    caen_code: str,
    judet: Optional[str] = None,
) -> dict:
    """Estimate addressable market by CAEN sector and optional county."""
    caen_2 = caen_code[:2]

    filters = [Company.caen_principal.like(f"{caen_2}%")]
    if judet:
        filters.append(Company.judet == judet)

    # Active companies
    active_count = (await db.execute(
        select(func.count()).select_from(Company)
        .where(and_(*filters, Company.stare == "ACTIVA"))
    )).scalar() or 0

    # Total including inactive
    total_count = (await db.execute(
        select(func.count()).select_from(Company).where(and_(*filters))
    )).scalar() or 0

    # Latest year aggregated financials
    latest_year = (await db.execute(
        select(func.max(FinancialData.an_fiscal))
        .join(Company, Company.id == FinancialData.company_id)
        .where(and_(*filters))
    )).scalar()

    market_data = {}
    if latest_year:
        agg = (await db.execute(
            select(
                func.sum(FinancialData.cifra_afaceri).label("total_ca"),
                func.sum(FinancialData.profit_net).label("total_profit"),
                func.sum(FinancialData.nr_angajati).label("total_emp"),
                func.avg(FinancialData.cifra_afaceri).label("avg_ca"),
            )
            .join(Company, Company.id == FinancialData.company_id)
            .where(and_(*filters, FinancialData.an_fiscal == latest_year))
        )).one()
        market_data = {
            "total_revenue": float(agg.total_ca or 0),
            "total_profit": float(agg.total_profit or 0),
            "total_employees": int(agg.total_emp or 0),
            "avg_revenue_per_company": round(float(agg.avg_ca or 0), 2),
        }

    # Top 5 by CA
    top_stmt = (
        select(Company.id, Company.denumire, FinancialData.cifra_afaceri)
        .join(FinancialData, FinancialData.company_id == Company.id)
        .where(and_(*filters, FinancialData.an_fiscal == latest_year))
        .order_by(FinancialData.cifra_afaceri.desc())
        .limit(5)
    )
    top = (await db.execute(top_stmt)).all()
    market_leaders = [
        {"company_id": t.id, "name": t.denumire, "revenue": float(t.cifra_afaceri or 0)}
        for t in top
    ]

    # Concentration: top 5 share
    if market_data.get("total_revenue", 0) > 0:
        top5_revenue = sum(l["revenue"] for l in market_leaders)
        hhi_top5 = round(top5_revenue / market_data["total_revenue"] * 100, 2)
    else:
        hhi_top5 = 0

    return {
        "caen_code": caen_code,
        "judet": judet,
        "latest_year": latest_year,
        "active_companies": active_count,
        "total_companies": total_count,
        "survival_rate": round(active_count / total_count * 100, 1) if total_count > 0 else 0,
        "market_data": market_data,
        "market_leaders": market_leaders,
        "concentration_top5_pct": hhi_top5,
    }


# ═══════════════════════════════════════════════════════════════════════
# 16.4  M&A TARGET SCREENING
# ═══════════════════════════════════════════════════════════════════════

async def ma_target_screening(
    db: AsyncSession,
    caen_code: str,
    min_ca: float = 0,
    max_ca: float = 100_000_000,
    min_margin: float = 0,
    limit: int = 20,
) -> dict:
    """Screen potential M&A targets matching financial criteria."""
    caen_2 = caen_code[:2]

    latest_year = (await db.execute(
        select(func.max(FinancialData.an_fiscal))
        .join(Company, Company.id == FinancialData.company_id)
        .where(Company.caen_principal.like(f"{caen_2}%"))
    )).scalar()

    if not latest_year:
        return {"caen_code": caen_code, "targets": [], "error": "Fără date disponibile"}

    stmt = (
        select(
            Company.id,
            Company.denumire,
            Company.cui,
            Company.caen_principal,
            Company.judet,
            Company.data_infiintare,
            FinancialData.cifra_afaceri,
            FinancialData.profit_net,
            FinancialData.nr_angajati,
            FinancialData.profit_margin,
            FinancialData.capitaluri_prop,
            FinancialData.total_datorii,
        )
        .join(FinancialData, FinancialData.company_id == Company.id)
        .where(
            and_(
                Company.caen_principal.like(f"{caen_2}%"),
                Company.stare == "ACTIVA",
                FinancialData.an_fiscal == latest_year,
                FinancialData.cifra_afaceri >= min_ca,
                FinancialData.cifra_afaceri <= max_ca,
                or_(FinancialData.profit_margin >= min_margin, FinancialData.profit_margin.is_(None)),
            )
        )
        .order_by(FinancialData.profit_margin.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    targets = []
    for r in rows:
        age = (date.today() - r.data_infiintare).days / 365.25 if r.data_infiintare else 0
        equity = float(r.capitaluri_prop or 0)
        debt = float(r.total_datorii or 0)

        # Simplified enterprise value estimate: equity + debt
        ev_estimate = equity + debt if equity > 0 else float(r.cifra_afaceri or 0) * 0.5

        targets.append({
            "company_id": r.id,
            "name": r.denumire,
            "cui": r.cui,
            "caen": r.caen_principal,
            "judet": r.judet,
            "age_years": round(age, 1),
            "cifra_afaceri": float(r.cifra_afaceri or 0),
            "profit_net": float(r.profit_net or 0),
            "profit_margin": round(float(r.profit_margin or 0), 2),
            "nr_angajati": r.nr_angajati or 0,
            "capitaluri_proprii": equity,
            "total_datorii": debt,
            "ev_estimate": round(ev_estimate, 0),
        })

    return {
        "caen_code": caen_code,
        "analysis_year": latest_year,
        "criteria": {"min_ca": min_ca, "max_ca": max_ca, "min_margin": min_margin},
        "targets": targets,
        "target_count": len(targets),
    }


# ═══════════════════════════════════════════════════════════════════════
# 16.5  PRICE INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════

async def price_intelligence(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """Revenue per employee, margin analytics, productivity metrics."""
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită"}

    fins = (await db.execute(
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.asc())
    )).scalars().all()

    if not fins:
        return {"company_id": company_id, "error": "Fără date financiare"}

    yearly_metrics = []
    for f in fins:
        ca = float(f.cifra_afaceri or 0)
        emp = f.nr_angajati or 0
        profit = float(f.profit_net or 0)
        assets = float(f.total_active or 0)

        rev_per_emp = round(ca / emp, 2) if emp > 0 else None
        profit_per_emp = round(profit / emp, 2) if emp > 0 else None
        asset_turnover = round(ca / assets, 4) if assets > 0 else None

        yearly_metrics.append({
            "year": f.an_fiscal,
            "revenue": ca,
            "profit": profit,
            "employees": emp,
            "revenue_per_employee": rev_per_emp,
            "profit_per_employee": profit_per_emp,
            "profit_margin": round(float(f.profit_margin or 0), 2),
            "asset_turnover": asset_turnover,
            "roa": round(float(f.roa or 0), 2),
            "roe": round(float(f.roe or 0), 2),
        })

    # Sector comparison for latest year
    latest = fins[-1]
    caen_2 = (company.caen_principal or "00")[:2]
    sector_avg = (await db.execute(
        select(
            func.avg(FinancialData.cifra_afaceri / func.nullif(FinancialData.nr_angajati, 0)).label("avg_rev_emp"),
            func.avg(FinancialData.profit_margin).label("avg_margin"),
        )
        .join(Company, Company.id == FinancialData.company_id)
        .where(
            and_(
                Company.caen_principal.like(f"{caen_2}%"),
                FinancialData.an_fiscal == latest.an_fiscal,
                FinancialData.nr_angajati > 0,
            )
        )
    )).one()

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "metrics": yearly_metrics,
        "sector_avg_rev_per_employee": round(float(sector_avg.avg_rev_emp or 0), 2),
        "sector_avg_margin": round(float(sector_avg.avg_margin or 0), 2),
    }
