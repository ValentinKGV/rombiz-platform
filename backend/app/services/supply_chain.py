"""
Supply Chain Risk — Branch 17.

Sub-modules:
  17.1  Supplier Network Discovery    — Map company suppliers via public contracts
  17.2  Dependency Mapping            — Identify critical supplier dependencies
  17.3  Disruption Alerts             — Flag suppliers with risk/insolvency issues
  17.4  Alternative Suppliers         — Find replacements in same CAEN
  17.5  Supply Chain Score            — Aggregate supply-chain risk assessment
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company, FinancialData, RiskScore,
    PublicContract, InsolvencyCase, CompanyDebt,
    EntityRelation, FraudAlert,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 17.1  SUPPLIER NETWORK DISCOVERY
# ═══════════════════════════════════════════════════════════════════════

async def discover_supplier_network(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Map supplier network using entity relations (FURNIZOR type)
    and public contract data.
    """
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită"}

    # Relations of type FURNIZOR / SUPPLIER / PARTENER
    rel_stmt = (
        select(
            EntityRelation.target_id,
            EntityRelation.relation_type,
            EntityRelation.weight,
            Company.denumire,
            Company.cui,
            Company.caen_principal,
            Company.judet,
            Company.stare,
        )
        .join(Company, Company.id == EntityRelation.target_id)
        .where(
            and_(
                EntityRelation.source_id == company_id,
                EntityRelation.source_type == "COMPANY",
                EntityRelation.target_type == "COMPANY",
                EntityRelation.relation_type.in_(["FURNIZOR", "SUPPLIER", "PARTENER", "SUBCONTRACTOR"]),
            )
        )
    )
    relations = (await db.execute(rel_stmt)).all()

    suppliers = []
    for r in relations:
        risk = (await db.execute(
            select(RiskScore.score, RiskScore.rating)
            .where(RiskScore.company_id == r.target_id)
        )).one_or_none()

        suppliers.append({
            "company_id": r.target_id,
            "name": r.denumire,
            "cui": r.cui,
            "caen": r.caen_principal,
            "judet": r.judet,
            "stare": r.stare,
            "relation_type": r.relation_type,
            "weight": float(r.weight) if r.weight else None,
            "risk_score": risk.score if risk else None,
            "risk_rating": risk.rating if risk else None,
        })

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "suppliers": suppliers,
        "supplier_count": len(suppliers),
        "active_suppliers": sum(1 for s in suppliers if s["stare"] == "ACTIVA"),
    }


# ═══════════════════════════════════════════════════════════════════════
# 17.2  DEPENDENCY MAPPING
# ═══════════════════════════════════════════════════════════════════════

async def dependency_mapping(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Identify critical supplier dependencies based on relation weight,
    shared CAEN sectors, and contract values.
    """
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită"}

    # All supplier relations
    rel_stmt = (
        select(
            EntityRelation.target_id,
            EntityRelation.relation_type,
            EntityRelation.weight,
            Company.denumire,
            Company.caen_principal,
        )
        .join(Company, Company.id == EntityRelation.target_id)
        .where(
            and_(
                EntityRelation.source_id == company_id,
                EntityRelation.source_type == "COMPANY",
                EntityRelation.target_type == "COMPANY",
            )
        )
    )
    relations = (await db.execute(rel_stmt)).all()

    # Group by CAEN to detect single-source dependencies
    caen_groups: dict[str, list] = {}
    dependencies = []
    for r in relations:
        caen_2 = (r.caen_principal or "00")[:2]
        caen_groups.setdefault(caen_2, []).append(r)

        weight_val = float(r.weight) if r.weight else 0.5

        dependency_level = "CRITICAL" if weight_val > 0.8 else "HIGH" if weight_val > 0.5 else "MEDIUM" if weight_val > 0.2 else "LOW"
        dependencies.append({
            "supplier_id": r.target_id,
            "supplier_name": r.denumire,
            "caen": r.caen_principal,
            "weight": weight_val,
            "dependency_level": dependency_level,
            "relation_type": r.relation_type,
        })

    # Identify single-source risks (CAEN with only 1 supplier)
    single_source_risks = [
        {"caen": caen, "supplier": group[0].denumire, "supplier_id": group[0].target_id}
        for caen, group in caen_groups.items() if len(group) == 1
    ]

    dependencies.sort(key=lambda x: x["weight"], reverse=True)

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "dependencies": dependencies,
        "single_source_risks": single_source_risks,
        "critical_dependencies": sum(1 for d in dependencies if d["dependency_level"] == "CRITICAL"),
        "total_dependencies": len(dependencies),
    }


# ═══════════════════════════════════════════════════════════════════════
# 17.3  DISRUPTION ALERTS
# ═══════════════════════════════════════════════════════════════════════

async def disruption_alerts(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Flag suppliers that have risk indicators (insolvency, debts, bad risk score).
    """
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită"}

    # Get supplier IDs
    supplier_ids_stmt = (
        select(EntityRelation.target_id)
        .where(
            and_(
                EntityRelation.source_id == company_id,
                EntityRelation.source_type == "COMPANY",
                EntityRelation.target_type == "COMPANY",
            )
        )
    )
    supplier_ids = [r for r in (await db.execute(supplier_ids_stmt)).scalars().all()]

    if not supplier_ids:
        return {"company_id": company_id, "alerts": [], "alert_count": 0}

    alerts = []

    for sid in supplier_ids:
        supplier = await db.get(Company, sid)
        if not supplier:
            continue

        supplier_alerts = []

        # Check insolvency
        insolvency_count = (await db.execute(
            select(func.count()).select_from(InsolvencyCase)
            .where(InsolvencyCase.company_id == sid)
        )).scalar() or 0
        if insolvency_count > 0:
            supplier_alerts.append({
                "type": "INSOLVENTA",
                "severity": "CRITICAL",
                "detail": f"{insolvency_count} proceduri insolvență",
            })

        # Check inactive
        if supplier.stare != "ACTIVA":
            supplier_alerts.append({
                "type": "INACTIV",
                "severity": "CRITICAL",
                "detail": f"Stare: {supplier.stare}",
            })

        # Check poor risk score
        risk = (await db.execute(
            select(RiskScore).where(RiskScore.company_id == sid)
        )).scalar_one_or_none()
        if risk and risk.score < 30:
            supplier_alerts.append({
                "type": "RISC_RIDICAT",
                "severity": "HIGH",
                "detail": f"Scor risc: {risk.score} ({risk.rating})",
            })

        # Check debts
        total_debt = float((await db.execute(
            select(func.sum(CompanyDebt.suma_restanta))
            .where(CompanyDebt.company_id == sid)
        )).scalar() or 0)
        if total_debt > 50000:
            supplier_alerts.append({
                "type": "DATORII_SEMNIFICATIVE",
                "severity": "HIGH",
                "detail": f"Datorii restante: {total_debt:,.0f} RON",
            })

        if supplier_alerts:
            alerts.append({
                "supplier_id": sid,
                "supplier_name": supplier.denumire,
                "supplier_cui": supplier.cui,
                "alerts": supplier_alerts,
                "max_severity": "CRITICAL" if any(a["severity"] == "CRITICAL" for a in supplier_alerts) else "HIGH",
            })

    alerts.sort(key=lambda x: 0 if x["max_severity"] == "CRITICAL" else 1)

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "alerts": alerts,
        "alert_count": len(alerts),
        "critical_count": sum(1 for a in alerts if a["max_severity"] == "CRITICAL"),
        "suppliers_monitored": len(supplier_ids),
    }


# ═══════════════════════════════════════════════════════════════════════
# 17.4  ALTERNATIVE SUPPLIERS
# ═══════════════════════════════════════════════════════════════════════

async def find_alternative_suppliers(
    db: AsyncSession,
    caen_code: str,
    judet: Optional[str] = None,
    limit: int = 15,
) -> dict:
    """Find potential alternative suppliers by CAEN sector."""
    caen_2 = caen_code[:2]

    filters = [
        Company.caen_principal.like(f"{caen_2}%"),
        Company.stare == "ACTIVA",
    ]
    if judet:
        filters.append(Company.judet == judet)

    latest_year = (await db.execute(
        select(func.max(FinancialData.an_fiscal))
    )).scalar()

    stmt = (
        select(
            Company.id,
            Company.denumire,
            Company.cui,
            Company.caen_principal,
            Company.judet,
            FinancialData.cifra_afaceri,
            FinancialData.nr_angajati,
            FinancialData.profit_margin,
            RiskScore.score.label("risk_score"),
            RiskScore.rating.label("risk_rating"),
        )
        .join(FinancialData, and_(
            FinancialData.company_id == Company.id,
            FinancialData.an_fiscal == latest_year,
        ), isouter=True)
        .join(RiskScore, RiskScore.company_id == Company.id, isouter=True)
        .where(and_(*filters))
        .order_by(FinancialData.cifra_afaceri.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    alternatives = []
    for r in rows:
        alternatives.append({
            "company_id": r.id,
            "name": r.denumire,
            "cui": r.cui,
            "caen": r.caen_principal,
            "judet": r.judet,
            "cifra_afaceri": float(r.cifra_afaceri or 0),
            "nr_angajati": r.nr_angajati or 0,
            "profit_margin": round(float(r.profit_margin or 0), 2),
            "risk_score": r.risk_score,
            "risk_rating": r.risk_rating,
        })

    return {
        "caen_code": caen_code,
        "judet": judet,
        "alternatives": alternatives,
        "count": len(alternatives),
    }


# ═══════════════════════════════════════════════════════════════════════
# 17.5  SUPPLY CHAIN SCORE
# ═══════════════════════════════════════════════════════════════════════

async def supply_chain_score(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """Aggregate supply chain risk score."""
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită"}

    # Get suppliers via relations
    supplier_ids_stmt = (
        select(EntityRelation.target_id, EntityRelation.weight)
        .where(
            and_(
                EntityRelation.source_id == company_id,
                EntityRelation.source_type == "COMPANY",
                EntityRelation.target_type == "COMPANY",
            )
        )
    )
    supplier_rows = (await db.execute(supplier_ids_stmt)).all()

    if not supplier_rows:
        return {
            "company_id": company_id,
            "company_name": company.denumire,
            "supply_chain_score": 100,
            "risk_level": "SCAZUT",
            "supplier_count": 0,
            "breakdown": {},
        }

    total_weight = sum(float(r.weight or 0.5) for r in supplier_rows) or 1
    weighted_risk = 0
    inactive_count = 0
    insolvent_count = 0
    high_risk_count = 0

    for row in supplier_rows:
        sid = row.target_id
        w = float(row.weight or 0.5) / total_weight

        supplier = await db.get(Company, sid)
        if not supplier:
            continue

        penalty = 0
        if supplier.stare != "ACTIVA":
            penalty += 40
            inactive_count += 1
        if supplier.has_insolvency:
            penalty += 30
            insolvent_count += 1

        risk = (await db.execute(
            select(RiskScore.score).where(RiskScore.company_id == sid)
        )).scalar()

        if risk:
            if risk < 30:
                penalty += 20
                high_risk_count += 1
            elif risk < 50:
                penalty += 10

        weighted_risk += penalty * w

    sc_score = max(0, round(100 - weighted_risk))

    if sc_score >= 80:
        risk_level = "SCAZUT"
    elif sc_score >= 50:
        risk_level = "MODERAT"
    elif sc_score >= 30:
        risk_level = "RIDICAT"
    else:
        risk_level = "CRITIC"

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "supply_chain_score": sc_score,
        "risk_level": risk_level,
        "supplier_count": len(supplier_rows),
        "breakdown": {
            "inactive_suppliers": inactive_count,
            "insolvent_suppliers": insolvent_count,
            "high_risk_suppliers": high_risk_count,
        },
    }
