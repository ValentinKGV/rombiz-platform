"""
Due Diligence Engine — Branch 15.

Sub-modules:
  15.1  Automated DD Checklist   — Generate a scored due diligence report
  15.2  Red Flag Detection       — Pattern-matched red flags across all domains
  15.3  Peer Comparison          — Compare company vs CAEN sector peers
  15.4  DD Report Generation     — Comprehensive due diligence document builder
  15.5  Compliance Scoring       — KYC/AML/PEP risk assessment
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company, FinancialData, RiskScore, ESGScore,
    InsolvencyCase, CourtCase, CompanyDebt,
    CompanyPerson, PublicContract, FraudAlert,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 15.1  AUTOMATED DD CHECKLIST
# ═══════════════════════════════════════════════════════════════════════

async def generate_dd_checklist(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Generate an automated due diligence checklist with pass/fail/warning
    for each check category.
    """
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită", "company_id": company_id}

    checks: list[dict] = []
    total_score = 0
    max_score = 0

    # 1. Legal existence
    legal_ok = company.stare == "ACTIVA"
    checks.append({
        "category": "EXISTENTA_LEGALA",
        "name": "Stare firmă",
        "status": "PASS" if legal_ok else "FAIL",
        "detail": f"Stare: {company.stare}",
        "weight": 15,
    })
    max_score += 15
    total_score += 15 if legal_ok else 0

    # 2. Registration age
    age_years = 0
    if company.data_infiintare:
        age_years = (date.today() - company.data_infiintare).days / 365.25
    age_ok = age_years >= 3
    checks.append({
        "category": "VECHIME",
        "name": "Vechime firmă",
        "status": "PASS" if age_ok else ("WARNING" if age_years >= 1 else "FAIL"),
        "detail": f"{age_years:.1f} ani (înregistrată: {company.data_infiintare})",
        "weight": 10,
    })
    max_score += 10
    total_score += 10 if age_ok else (5 if age_years >= 1 else 0)

    # 3. Financial data available
    fin_stmt = (
        select(func.count())
        .select_from(FinancialData)
        .where(FinancialData.company_id == company_id)
    )
    fin_count = (await db.execute(fin_stmt)).scalar() or 0
    fin_ok = fin_count >= 2
    checks.append({
        "category": "DATE_FINANCIARE",
        "name": "Disponibilitate date financiare",
        "status": "PASS" if fin_ok else ("WARNING" if fin_count >= 1 else "FAIL"),
        "detail": f"{fin_count} ani de bilanțuri disponibile",
        "weight": 10,
    })
    max_score += 10
    total_score += 10 if fin_ok else (5 if fin_count >= 1 else 0)

    # 4. No insolvency
    insolvency_stmt = (
        select(func.count())
        .select_from(InsolvencyCase)
        .where(InsolvencyCase.company_id == company_id)
    )
    insolvency_count = (await db.execute(insolvency_stmt)).scalar() or 0
    insolvency_ok = insolvency_count == 0
    checks.append({
        "category": "INSOLVENTA",
        "name": "Fără proceduri de insolvență",
        "status": "PASS" if insolvency_ok else "FAIL",
        "detail": f"{insolvency_count} proceduri de insolvență",
        "weight": 15,
    })
    max_score += 15
    total_score += 15 if insolvency_ok else 0

    # 5. No outstanding debts
    debt_stmt = (
        select(func.sum(CompanyDebt.suma_restanta))
        .where(CompanyDebt.company_id == company_id)
    )
    total_debt = float((await db.execute(debt_stmt)).scalar() or 0)
    debt_ok = total_debt == 0
    checks.append({
        "category": "DATORII",
        "name": "Fără datorii restante la stat",
        "status": "PASS" if debt_ok else ("WARNING" if total_debt < 50000 else "FAIL"),
        "detail": f"Datorii restante: {total_debt:,.0f} RON",
        "weight": 15,
    })
    max_score += 15
    total_score += 15 if debt_ok else (7 if total_debt < 50000 else 0)

    # 6. Fiscal compliance
    fiscal_ok = not company.inactiv_fiscal
    checks.append({
        "category": "FISCAL",
        "name": "Conformitate fiscală",
        "status": "PASS" if fiscal_ok else "FAIL",
        "detail": "Inactiv fiscal" if not fiscal_ok else "Activ fiscal",
        "weight": 10,
    })
    max_score += 10
    total_score += 10 if fiscal_ok else 0

    # 7. Court cases
    court_stmt = (
        select(func.count())
        .select_from(CourtCase)
        .where(CourtCase.company_id == company_id)
    )
    court_count = (await db.execute(court_stmt)).scalar() or 0
    court_ok = court_count <= 2
    checks.append({
        "category": "LITIGII",
        "name": "Dosare în instanță",
        "status": "PASS" if court_count == 0 else ("WARNING" if court_ok else "FAIL"),
        "detail": f"{court_count} dosare",
        "weight": 10,
    })
    max_score += 10
    total_score += 10 if court_count == 0 else (5 if court_ok else 0)

    # 8. Risk score
    risk = (await db.execute(
        select(RiskScore).where(RiskScore.company_id == company_id)
    )).scalar_one_or_none()
    risk_ok = risk and risk.score >= 60
    checks.append({
        "category": "SCOR_RISC",
        "name": "Scor de risc acceptabil",
        "status": "PASS" if risk_ok else ("WARNING" if risk and risk.score >= 40 else "FAIL"),
        "detail": f"Scor: {risk.score if risk else 'N/A'} ({risk.rating if risk else 'N/A'})",
        "weight": 10,
    })
    max_score += 10
    total_score += 10 if risk_ok else (5 if risk and risk.score >= 40 else 0)

    # 9. Positive equity
    latest_fin_stmt = (
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.desc())
        .limit(1)
    )
    latest_fin = (await db.execute(latest_fin_stmt)).scalar_one_or_none()
    equity_ok = latest_fin and latest_fin.capitaluri_prop and latest_fin.capitaluri_prop > 0
    checks.append({
        "category": "CAPITALURI",
        "name": "Capitaluri proprii pozitive",
        "status": "PASS" if equity_ok else "FAIL",
        "detail": f"Capitaluri: {latest_fin.capitaluri_prop:,} RON" if latest_fin and latest_fin.capitaluri_prop else "N/A",
        "weight": 5,
    })
    max_score += 5
    total_score += 5 if equity_ok else 0

    # Overall score
    dd_score = round((total_score / max_score * 100)) if max_score > 0 else 0
    if dd_score >= 80:
        dd_verdict = "FAVORABIL"
    elif dd_score >= 50:
        dd_verdict = "CONDITIONAT"
    else:
        dd_verdict = "NEFAVORABIL"

    passed = sum(1 for c in checks if c["status"] == "PASS")
    warnings = sum(1 for c in checks if c["status"] == "WARNING")
    failed = sum(1 for c in checks if c["status"] == "FAIL")

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "dd_score": dd_score,
        "verdict": dd_verdict,
        "checks": checks,
        "summary": {
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "total": len(checks),
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# 15.2  RED FLAG DETECTION
# ═══════════════════════════════════════════════════════════════════════

async def detect_red_flags(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Scan for red flags across all data domains.
    """
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită", "company_id": company_id}

    red_flags: list[dict] = []

    # RF1: Recently created but high capital
    if company.data_infiintare:
        age = (date.today() - company.data_infiintare).days / 365.25
        if age < 1 and company.capital_social and company.capital_social > 100000:
            red_flags.append({
                "flag": "FIRMA_NOUA_CAPITAL_MARE",
                "severity": "MEDIUM",
                "detail": f"Firmă de {age:.1f} ani cu capital social {company.capital_social:,.0f} RON",
                "category": "STRUCTURAL",
            })

    # RF2: Inactive fiscal
    if company.inactiv_fiscal:
        red_flags.append({
            "flag": "INACTIV_FISCAL",
            "severity": "HIGH",
            "detail": "Declarată inactivă fiscal de ANAF",
            "category": "FISCAL",
        })

    # RF3: Multiple insolvencies
    insolvency_count = (await db.execute(
        select(func.count()).select_from(InsolvencyCase)
        .where(InsolvencyCase.company_id == company_id)
    )).scalar() or 0
    if insolvency_count > 0:
        red_flags.append({
            "flag": "INSOLVENTA_ACTIVA",
            "severity": "CRITICAL",
            "detail": f"{insolvency_count} proceduri de insolvență",
            "category": "LEGAL",
        })

    # RF4: High outstanding debts
    total_debt = float((await db.execute(
        select(func.sum(CompanyDebt.suma_restanta))
        .where(CompanyDebt.company_id == company_id)
    )).scalar() or 0)
    if total_debt > 100000:
        red_flags.append({
            "flag": "DATORII_MARI",
            "severity": "HIGH",
            "detail": f"Datorii restante: {total_debt:,.0f} RON",
            "category": "FISCAL",
        })

    # RF5: Negative equity
    latest_fin = (await db.execute(
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.desc())
        .limit(1)
    )).scalar_one_or_none()

    if latest_fin and latest_fin.capitaluri_prop is not None and latest_fin.capitaluri_prop < 0:
        red_flags.append({
            "flag": "CAPITALURI_NEGATIVE",
            "severity": "HIGH",
            "detail": f"Capitaluri proprii: {latest_fin.capitaluri_prop:,} RON",
            "category": "FINANCIAR",
        })

    # RF6: Revenue crash
    fins = (await db.execute(
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.desc())
        .limit(2)
    )).scalars().all()
    if len(fins) >= 2:
        ca_now = float(fins[0].cifra_afaceri or 0)
        ca_prev = float(fins[1].cifra_afaceri or 1)
        if ca_prev > 0 and ca_now / ca_prev < 0.5:
            red_flags.append({
                "flag": "SCADERE_CA_MAJORA",
                "severity": "HIGH",
                "detail": f"CA a scăzut cu {((1 - ca_now / ca_prev) * 100):.0f}% într-un an",
                "category": "FINANCIAR",
            })

    # RF7: No employees but high revenue
    if latest_fin:
        ca = float(latest_fin.cifra_afaceri or 0)
        emp = latest_fin.nr_angajati or 0
        if ca > 5000000 and emp == 0:
            red_flags.append({
                "flag": "CA_FARA_ANGAJATI",
                "severity": "MEDIUM",
                "detail": f"CA: {ca:,.0f} RON cu 0 angajați",
                "category": "STRUCTURAL",
            })

    # RF8: Many court cases
    court_count = (await db.execute(
        select(func.count()).select_from(CourtCase)
        .where(CourtCase.company_id == company_id)
    )).scalar() or 0
    if court_count > 5:
        red_flags.append({
            "flag": "LITIGII_MULTIPLE",
            "severity": "MEDIUM",
            "detail": f"{court_count} dosare în instanță",
            "category": "LEGAL",
        })

    # RF9: Fraud alerts
    fraud_count = (await db.execute(
        select(func.count()).select_from(FraudAlert)
        .where(
            and_(
                FraudAlert.company_id == company_id,
                FraudAlert.status == "OPEN",
            )
        )
    )).scalar() or 0
    if fraud_count > 0:
        red_flags.append({
            "flag": "ALERTE_FRAUDA",
            "severity": "CRITICAL",
            "detail": f"{fraud_count} alerte de fraudă deschise",
            "category": "FRAUDA",
        })

    # RF10: Frequent admin changes
    admin_changes = (await db.execute(
        select(func.count()).select_from(CompanyPerson)
        .where(
            and_(
                CompanyPerson.company_id == company_id,
                CompanyPerson.tip == "ADMINISTRATOR",
                CompanyPerson.activ.is_(False),
            )
        )
    )).scalar() or 0
    if admin_changes > 3:
        red_flags.append({
            "flag": "SCHIMBARI_ADMIN_FRECVENTE",
            "severity": "MEDIUM",
            "detail": f"{admin_changes} administratori schimbați",
            "category": "GUVERNANTA",
        })

    # Severity sort
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    red_flags.sort(key=lambda x: severity_order.get(x["severity"], 4))

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "red_flags": red_flags,
        "red_flags_count": len(red_flags),
        "critical_count": sum(1 for f in red_flags if f["severity"] == "CRITICAL"),
        "high_count": sum(1 for f in red_flags if f["severity"] == "HIGH"),
        "risk_level": "CRITIC" if any(f["severity"] == "CRITICAL" for f in red_flags)
                      else "RIDICAT" if any(f["severity"] == "HIGH" for f in red_flags)
                      else "MODERAT" if red_flags else "SCAZUT",
    }


# ═══════════════════════════════════════════════════════════════════════
# 15.3  PEER COMPARISON
# ═══════════════════════════════════════════════════════════════════════

async def compare_peers(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Compare company financial metrics against CAEN sector peers.
    """
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită", "company_id": company_id}

    caen_prefix = (company.caen_principal or "00")[:2]

    # Company latest financials
    latest_fin = (await db.execute(
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.desc())
        .limit(1)
    )).scalar_one_or_none()

    if not latest_fin:
        return {
            "company_id": company_id,
            "error": "Fără date financiare disponibile",
        }

    # Sector averages for same year
    sector_stmt = (
        select(
            func.avg(FinancialData.cifra_afaceri).label("avg_ca"),
            func.avg(FinancialData.profit_net).label("avg_profit"),
            func.avg(FinancialData.nr_angajati).label("avg_emp"),
            func.avg(FinancialData.rata_lichiditate).label("avg_lichid"),
            func.avg(FinancialData.grad_indatorare).label("avg_indatorare"),
            func.avg(FinancialData.roa).label("avg_roa"),
            func.avg(FinancialData.roe).label("avg_roe"),
            func.avg(FinancialData.profit_margin).label("avg_margin"),
            func.count(FinancialData.id).label("peer_count"),
            func.percentile_cont(0.5).within_group(FinancialData.cifra_afaceri).label("median_ca"),
        )
        .join(Company, Company.id == FinancialData.company_id)
        .where(
            and_(
                Company.caen_principal.like(f"{caen_prefix}%"),
                FinancialData.an_fiscal == latest_fin.an_fiscal,
                Company.stare == "ACTIVA",
            )
        )
    )

    try:
        sector_result = (await db.execute(sector_stmt)).one()
    except Exception:
        # Fallback without percentile_cont for SQLite
        fallback_stmt = (
            select(
                func.avg(FinancialData.cifra_afaceri).label("avg_ca"),
                func.avg(FinancialData.profit_net).label("avg_profit"),
                func.avg(FinancialData.nr_angajati).label("avg_emp"),
                func.avg(FinancialData.rata_lichiditate).label("avg_lichid"),
                func.avg(FinancialData.grad_indatorare).label("avg_indatorare"),
                func.avg(FinancialData.roa).label("avg_roa"),
                func.avg(FinancialData.roe).label("avg_roe"),
                func.avg(FinancialData.profit_margin).label("avg_margin"),
                func.count(FinancialData.id).label("peer_count"),
            )
            .join(Company, Company.id == FinancialData.company_id)
            .where(
                and_(
                    Company.caen_principal.like(f"{caen_prefix}%"),
                    FinancialData.an_fiscal == latest_fin.an_fiscal,
                    Company.stare == "ACTIVA",
                )
            )
        )
        sector_result = (await db.execute(fallback_stmt)).one()

    def _compare(company_val, sector_avg, higher_is_better=True):
        if company_val is None or sector_avg is None or float(sector_avg) == 0:
            return {"value": float(company_val) if company_val else None,
                    "sector_avg": float(sector_avg) if sector_avg else None,
                    "percentile_estimate": None, "verdict": "INSUFICIENT_DATE"}
        ratio = float(company_val) / float(sector_avg)
        if higher_is_better:
            verdict = "PESTE_MEDIE" if ratio > 1.1 else ("LA_MEDIE" if ratio > 0.9 else "SUB_MEDIE")
        else:
            verdict = "PESTE_MEDIE" if ratio < 0.9 else ("LA_MEDIE" if ratio < 1.1 else "SUB_MEDIE")
        return {
            "value": round(float(company_val), 2),
            "sector_avg": round(float(sector_avg), 2),
            "ratio": round(ratio, 4),
            "verdict": verdict,
        }

    comparisons = {
        "cifra_afaceri": _compare(latest_fin.cifra_afaceri, sector_result.avg_ca),
        "profit_net": _compare(latest_fin.profit_net, sector_result.avg_profit),
        "nr_angajati": _compare(latest_fin.nr_angajati, sector_result.avg_emp),
        "rata_lichiditate": _compare(latest_fin.rata_lichiditate, sector_result.avg_lichid),
        "grad_indatorare": _compare(latest_fin.grad_indatorare, sector_result.avg_indatorare, higher_is_better=False),
        "roa": _compare(latest_fin.roa, sector_result.avg_roa),
        "roe": _compare(latest_fin.roe, sector_result.avg_roe),
        "profit_margin": _compare(latest_fin.profit_margin, sector_result.avg_margin),
    }

    # Overall performance
    above = sum(1 for c in comparisons.values() if c.get("verdict") == "PESTE_MEDIE")
    below = sum(1 for c in comparisons.values() if c.get("verdict") == "SUB_MEDIE")
    overall = "PERFORMANTA_SUPERIOARA" if above >= 5 else "PERFORMANTA_MEDIE" if above >= 3 else "PERFORMANTA_INFERIOARA"

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "caen_code": company.caen_principal,
        "analysis_year": latest_fin.an_fiscal,
        "peer_count": sector_result.peer_count,
        "comparisons": comparisons,
        "above_average_count": above,
        "below_average_count": below,
        "overall_performance": overall,
    }


# ═══════════════════════════════════════════════════════════════════════
# 15.4  DD REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════

async def generate_dd_report(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Comprehensive DD report aggregating all sub-analyses.
    """
    checklist = await generate_dd_checklist(db, company_id)
    if "error" in checklist:
        return checklist

    red_flags = await detect_red_flags(db, company_id)
    peers = await compare_peers(db, company_id)

    # Fetch additional context
    company = await db.get(Company, company_id)
    risk = (await db.execute(
        select(RiskScore).where(RiskScore.company_id == company_id)
    )).scalar_one_or_none()
    esg = (await db.execute(
        select(ESGScore).where(ESGScore.company_id == company_id)
    )).scalar_one_or_none()

    return {
        "company_id": company_id,
        "company_name": company.denumire if company else "N/A",
        "cui": company.cui if company else None,
        "report_date": datetime.now(timezone.utc).isoformat(),
        "dd_score": checklist["dd_score"],
        "verdict": checklist["verdict"],
        "checklist": checklist["checks"],
        "checklist_summary": checklist["summary"],
        "red_flags": red_flags.get("red_flags", []),
        "red_flags_risk_level": red_flags.get("risk_level", "SCAZUT"),
        "peer_comparison": peers.get("comparisons"),
        "peer_performance": peers.get("overall_performance"),
        "risk_score": {
            "score": risk.score if risk else None,
            "rating": risk.rating if risk else None,
            "probabilitate_insolventa": float(risk.probabilitate_insolventa) if risk and risk.probabilitate_insolventa else None,
        },
        "esg_score": {
            "total": float(esg.score_total) if esg and esg.score_total else None,
            "rating": esg.esg_rating if esg else None,
        },
        "disclaimer": (
            "Acest raport de due diligence este generat automat din surse publice. "
            "Nu înlocuiește o due diligence profesională și nu garantează exhaustivitatea informațiilor."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════
# 15.5  COMPLIANCE SCORING (KYC/AML)
# ═══════════════════════════════════════════════════════════════════════

async def compliance_scoring(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    KYC/AML compliance risk assessment.
    """
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită", "company_id": company_id}

    risk_factors: list[dict] = []
    compliance_score = 100  # start at 100, deduct points

    # High-risk jurisdictions (simplified — Romanian counties with known risks)
    # In practice, this would check against international sanctions lists
    if company.stare != "ACTIVA":
        compliance_score -= 30
        risk_factors.append({
            "factor": "FIRMA_INACTIVA",
            "impact": -30,
            "detail": f"Stare: {company.stare}",
        })

    # Young company
    if company.data_infiintare:
        age = (date.today() - company.data_infiintare).days / 365.25
        if age < 1:
            compliance_score -= 15
            risk_factors.append({
                "factor": "FIRMA_FOARTE_TANARA",
                "impact": -15,
                "detail": f"Vechime: {age:.1f} ani",
            })

    # Inactive fiscal
    if company.inactiv_fiscal:
        compliance_score -= 25
        risk_factors.append({
            "factor": "INACTIV_FISCAL",
            "impact": -25,
            "detail": "Declarată inactivă fiscal de ANAF",
        })

    # Insolvency
    if company.has_insolvency:
        compliance_score -= 20
        risk_factors.append({
            "factor": "INSOLVENTA",
            "impact": -20,
            "detail": "Procedură de insolvență în derulare",
        })

    # Debts
    if company.has_debts:
        compliance_score -= 10
        risk_factors.append({
            "factor": "DATORII_RESTANTE",
            "impact": -10,
            "detail": "Datorii restante la bugetul de stat",
        })

    # Fraud alerts
    fraud_count = (await db.execute(
        select(func.count()).select_from(FraudAlert)
        .where(
            and_(FraudAlert.company_id == company_id, FraudAlert.status == "OPEN")
        )
    )).scalar() or 0
    if fraud_count > 0:
        compliance_score -= 20
        risk_factors.append({
            "factor": "ALERTE_FRAUDA",
            "impact": -20,
            "detail": f"{fraud_count} alerte de fraudă deschise",
        })

    # Admin changes
    admin_stmt = (
        select(func.count()).select_from(CompanyPerson)
        .where(
            and_(
                CompanyPerson.company_id == company_id,
                CompanyPerson.tip == "ADMINISTRATOR",
            )
        )
    )
    admin_total = (await db.execute(admin_stmt)).scalar() or 0
    active_admin = (await db.execute(
        select(func.count()).select_from(CompanyPerson)
        .where(
            and_(
                CompanyPerson.company_id == company_id,
                CompanyPerson.tip == "ADMINISTRATOR",
                CompanyPerson.activ.is_(True),
            )
        )
    )).scalar() or 0

    if admin_total > 5 and active_admin <= 1:
        compliance_score -= 10
        risk_factors.append({
            "factor": "TURNOVER_MANAGEMENT",
            "impact": -10,
            "detail": f"Turnover ridicat management: {admin_total} total, {active_admin} activi",
        })

    compliance_score = max(0, compliance_score)

    if compliance_score >= 80:
        kyc_level = "LOW_RISK"
    elif compliance_score >= 50:
        kyc_level = "MEDIUM_RISK"
    else:
        kyc_level = "HIGH_RISK"

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "compliance_score": compliance_score,
        "kyc_risk_level": kyc_level,
        "risk_factors": risk_factors,
        "risk_factors_count": len(risk_factors),
        "recommendations": _generate_recommendations(kyc_level, risk_factors),
    }


def _generate_recommendations(level: str, factors: list[dict]) -> list[str]:
    """Generate compliance recommendations."""
    recs = []
    if level == "HIGH_RISK":
        recs.append("Verificare manuală obligatorie înainte de onboarding")
        recs.append("Solicitare documente suplimentare de identificare")
    if any(f["factor"] == "INSOLVENTA" for f in factors):
        recs.append("Verificare stare procedură insolvență la tribunal")
    if any(f["factor"] == "ALERTE_FRAUDA" for f in factors):
        recs.append("Investigare detaliată alerte de fraudă")
    if any(f["factor"] == "INACTIV_FISCAL" for f in factors):
        recs.append("Confirmare reactivare fiscală de la ANAF")
    if not recs:
        recs.append("Monitorizare periodică standard")
    return recs
