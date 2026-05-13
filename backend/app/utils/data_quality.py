"""
Data Quality Score computation.

Calculates a 0–100 score reflecting how complete and fresh a company's data is.
Uses weighted checks across identity fields, financials, relationships, etc.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.models import (
    Company,
    FinancialData,
    CompanyPerson,
    RiskScore,
    ESGScore,
    CompanyDebt,
    PublicContract,
    CourtCase,
    InsolvencyCase,
    EUProject,
    CompanyMention,
)

logger = get_logger(__name__)

# ── Weight table (sums to 100) ────────────────────────────────────────
WEIGHTS = {
    "identity":     15,   # CUI, name, forma juridica, J‑nr
    "address":      10,   # full address, county, locality, geocode
    "fiscal":        8,   # TVA status, inactiv fiscal flags
    "financials":   20,   # at least 1 year of financial data
    "persons":      10,   # at least 1 associated person
    "risk_score":    8,   # risk assessment computed
    "esg_score":     5,   # ESG assessment present
    "data_sources":  8,   # multiple data sources synced
    "enrichment":   10,   # debts, contracts, court, insolvency checks
    "freshness":     6,   # updated within last 30 days
}

assert sum(WEIGHTS.values()) == 100, "Weights must sum to 100"


async def compute_score(company: Company, db: AsyncSession) -> int:
    """
    Compute data quality score for a single company.
    Returns an integer 0–100.
    """
    score = 0.0

    # ── 1. Identity completeness (15 pts) ────────────────────────
    identity_fields = [
        company.cui is not None,
        bool(company.denumire),
        bool(company.forma_juridica),
        bool(company.j_nr),
        company.data_infiintare is not None,
    ]
    score += WEIGHTS["identity"] * (sum(identity_fields) / len(identity_fields))

    # ── 2. Address (10 pts) ──────────────────────────────────────
    address_fields = [
        bool(company.adresa_completa),
        bool(company.judet),
        bool(company.localitate),
        bool(company.cod_postal),
        company.lat is not None and company.lng is not None,
    ]
    score += WEIGHTS["address"] * (sum(address_fields) / len(address_fields))

    # ── 3. Fiscal status (8 pts) — all flags set = 100 % ────────
    # Even having default False is valid (it means checked).
    # Award full points if we know the fiscal status indicators exist on the company.
    fiscal_known = 4  # platitor_tva, tva_la_incasare, split_tva, inactiv_fiscal
    score += WEIGHTS["fiscal"]  # always fully available on the model

    # ── 4. Financial data (20 pts) ───────────────────────────────
    fin_count = await db.scalar(
        select(func.count()).select_from(FinancialData).where(
            FinancialData.company_id == company.id
        )
    ) or 0
    if fin_count >= 3:
        score += WEIGHTS["financials"]
    elif fin_count >= 1:
        score += WEIGHTS["financials"] * 0.6
    # 0 years → 0 pts

    # ── 5. Persons / administrators (10 pts) ─────────────────────
    person_count = await db.scalar(
        select(func.count()).select_from(CompanyPerson).where(
            CompanyPerson.company_id == company.id
        )
    ) or 0
    if person_count >= 1:
        score += WEIGHTS["persons"]

    # ── 6. Risk score computed (8 pts) ───────────────────────────
    has_risk = await db.scalar(
        select(func.count()).select_from(RiskScore).where(
            RiskScore.company_id == company.id
        )
    )
    if has_risk:
        score += WEIGHTS["risk_score"]

    # ── 7. ESG score (5 pts) ─────────────────────────────────────
    has_esg = await db.scalar(
        select(func.count()).select_from(ESGScore).where(
            ESGScore.company_id == company.id
        )
    )
    if has_esg:
        score += WEIGHTS["esg_score"]

    # ── 8. Data sources breadth (8 pts) ──────────────────────────
    sources = company.data_sources or {}
    num_sources = len(sources)
    if num_sources >= 5:
        score += WEIGHTS["data_sources"]
    elif num_sources >= 3:
        score += WEIGHTS["data_sources"] * 0.7
    elif num_sources >= 1:
        score += WEIGHTS["data_sources"] * 0.4

    # ── 9. Enrichment checks (10 pts) ────────────────────────────
    # Each flag indicates the data dimension was checked / enriched.
    enrichment_flags = [
        company.has_debts is not None,
        company.has_insolvency is not None,
        company.has_litigation is not None,
        company.has_seap_contracts is not None,
        company.has_eu_projects is not None,
        company.has_trademarks is not None,
        bool(company.caen_principal),
        company.capital_social is not None,
    ]
    score += WEIGHTS["enrichment"] * (sum(enrichment_flags) / len(enrichment_flags))

    # ── 10. Freshness (6 pts) ────────────────────────────────────
    if company.updated_at:
        days_old = (datetime.now(timezone.utc) - company.updated_at.replace(
            tzinfo=timezone.utc if company.updated_at.tzinfo is None else company.updated_at.tzinfo
        )).days
        if days_old <= 7:
            score += WEIGHTS["freshness"]
        elif days_old <= 30:
            score += WEIGHTS["freshness"] * 0.7
        elif days_old <= 90:
            score += WEIGHTS["freshness"] * 0.3

    return min(100, max(0, int(round(score))))


async def update_company_score(company_id: int, db: AsyncSession) -> int:
    """Compute and persist data quality score for one company."""
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    if company is None:
        return 0

    new_score = await compute_score(company, db)
    company.data_quality_score = new_score
    await db.commit()

    logger.info(
        "data_quality_updated",
        company_id=company_id,
        cui=company.cui,
        score=new_score,
    )
    return new_score


async def batch_update_scores(db: AsyncSession, limit: int = 1000) -> dict:
    """
    Re-compute data quality scores for companies.
    Processes oldest-updated first.
    """
    result = await db.execute(
        select(Company)
        .order_by(Company.updated_at.asc())
        .limit(limit)
    )
    companies = result.scalars().all()

    updated = 0
    for company in companies:
        try:
            new_score = await compute_score(company, db)
            if company.data_quality_score != new_score:
                company.data_quality_score = new_score
                updated += 1
        except Exception as e:
            logger.error(
                "quality_score_failed",
                company_id=company.id,
                error=str(e),
            )

    await db.commit()
    logger.info("batch_quality_update", total=len(companies), updated=updated)
    return {"total": len(companies), "updated": updated}
