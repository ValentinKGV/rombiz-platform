"""
Regulatory Compliance — Branch 19.

Sub-modules:
  19.1  GDPR Compliance Check     — Assess data protection compliance
  19.2  Fiscal Compliance         — Tax obligation verification
  19.3  Environmental Compliance  — Environmental regulation checks
  19.4  Labor Law Compliance      — Employment law assessment
  19.5  AML Compliance            — Anti-money laundering assessment
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company, FinancialData, CompanyDebt, EnvironmentalFine,
    CompanyPerson, InsolvencyCase, FraudAlert,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 19.1  GDPR COMPLIANCE CHECK
# ═══════════════════════════════════════════════════════════════════════

async def gdpr_compliance_check(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Assess GDPR compliance posture based on available data.
    """
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită"}

    checks = []
    score = 0
    max_score = 0

    # Check if company has employees (GDPR requires DPO for large companies)
    latest_fin = (await db.execute(
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.desc())
        .limit(1)
    )).scalar_one_or_none()

    emp_count = latest_fin.nr_angajati if latest_fin else 0

    # DPO requirement
    needs_dpo = emp_count >= 250
    checks.append({
        "check": "DPO_REQUIREMENT",
        "name": "Necesitate DPO",
        "status": "INFO" if not needs_dpo else "WARNING",
        "detail": f"{'Necesită DPO (>250 angajați)' if needs_dpo else 'DPO nu este obligatoriu (<250 angajați)'}",
        "weight": 15,
    })
    max_score += 15
    score += 15 if not needs_dpo else 8

    # CAEN check — high-risk categories for GDPR
    high_risk_caen = ["6201", "6202", "6311", "6312", "6399", "8010", "8020"]
    caen = company.caen_principal or ""
    is_high_risk = any(caen.startswith(c[:2]) for c in high_risk_caen)
    checks.append({
        "check": "HIGH_RISK_PROCESSING",
        "name": "Procesare date cu risc ridicat",
        "status": "WARNING" if is_high_risk else "PASS",
        "detail": f"CAEN {caen}: {'sector cu risc ridicat GDPR' if is_high_risk else 'sector cu risc standard'}",
        "weight": 20,
    })
    max_score += 20
    score += 10 if is_high_risk else 20

    # Company active status
    is_active = company.stare == "ACTIVA"
    checks.append({
        "check": "COMPANY_STATUS",
        "name": "Stare activă",
        "status": "PASS" if is_active else "FAIL",
        "detail": f"Stare: {company.stare}",
        "weight": 15,
    })
    max_score += 15
    score += 15 if is_active else 0

    # Data retention (inferred)
    age = 0
    if company.data_infiintare:
        age = (date.today() - company.data_infiintare).days / 365.25
    checks.append({
        "check": "DATA_RETENTION",
        "name": "Politică de retenție date",
        "status": "INFO",
        "detail": f"Companie veche de {age:.0f} ani — necesită politică de retenție a datelor personale",
        "weight": 10,
    })
    max_score += 10
    score += 10  # Info only

    gdpr_score = round(score / max_score * 100) if max_score else 0

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "gdpr_score": gdpr_score,
        "risk_level": "RIDICAT" if gdpr_score < 50 else "MODERAT" if gdpr_score < 75 else "SCAZUT",
        "checks": checks,
        "recommendations": [
            "Desemnare responsabil protecția datelor (DPO)" if needs_dpo else None,
            "Implementare registru de prelucrări" if is_high_risk else None,
            "Evaluare impact asupra protecției datelor (DPIA)" if is_high_risk else None,
            "Actualizare politici de confidențialitate",
        ],
    }


# ═══════════════════════════════════════════════════════════════════════
# 19.2  FISCAL COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════

async def fiscal_compliance(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """Tax compliance verification."""
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită"}

    checks = []
    score = 0
    max_score = 0

    # 1. Fiscal activity status
    is_active_fiscal = not company.inactiv_fiscal
    checks.append({
        "check": "STARE_FISCALA",
        "name": "Activitate fiscală",
        "status": "PASS" if is_active_fiscal else "FAIL",
        "detail": "Activ fiscal" if is_active_fiscal else "INACTIV FISCAL — declarat de ANAF",
        "weight": 25,
    })
    max_score += 25
    score += 25 if is_active_fiscal else 0

    # 2. Outstanding debts
    total_debt = float((await db.execute(
        select(func.sum(CompanyDebt.suma_restanta))
        .where(CompanyDebt.company_id == company_id)
    )).scalar() or 0)

    debt_count = (await db.execute(
        select(func.count()).select_from(CompanyDebt)
        .where(CompanyDebt.company_id == company_id)
    )).scalar() or 0

    checks.append({
        "check": "DATORII_BUGET",
        "name": "Obligații bugetare restante",
        "status": "PASS" if total_debt == 0 else ("WARNING" if total_debt < 10000 else "FAIL"),
        "detail": f"{debt_count} tipuri de datorii, total: {total_debt:,.0f} RON",
        "weight": 25,
    })
    max_score += 25
    score += 25 if total_debt == 0 else (12 if total_debt < 10000 else 0)

    # 3. VAT registration
    is_vat = company.platitor_tva
    checks.append({
        "check": "PLATITOR_TVA",
        "name": "Înregistrare TVA",
        "status": "INFO",
        "detail": "Plătitor de TVA" if is_vat else "Nu este plătitor de TVA",
        "weight": 10,
    })
    max_score += 10
    score += 10

    # 4. Financial reporting compliance
    fin_count = (await db.execute(
        select(func.count()).select_from(FinancialData)
        .where(FinancialData.company_id == company_id)
    )).scalar() or 0
    checks.append({
        "check": "RAPORTARE_FINANCIARA",
        "name": "Raportare financiară",
        "status": "PASS" if fin_count >= 3 else ("WARNING" if fin_count >= 1 else "FAIL"),
        "detail": f"{fin_count} bilanțuri depuse",
        "weight": 20,
    })
    max_score += 20
    score += 20 if fin_count >= 3 else (10 if fin_count >= 1 else 0)

    # 5. Insolvency status
    insolvency_count = (await db.execute(
        select(func.count()).select_from(InsolvencyCase)
        .where(InsolvencyCase.company_id == company_id)
    )).scalar() or 0
    checks.append({
        "check": "INSOLVENTA",
        "name": "Proceduri insolvență",
        "status": "PASS" if insolvency_count == 0 else "FAIL",
        "detail": f"{insolvency_count} proceduri" if insolvency_count else "Nicio procedură",
        "weight": 20,
    })
    max_score += 20
    score += 20 if insolvency_count == 0 else 0

    fiscal_score = round(score / max_score * 100) if max_score else 0

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "fiscal_score": fiscal_score,
        "status": "CONFORM" if fiscal_score >= 80 else "PARTIAL_CONFORM" if fiscal_score >= 50 else "NECONFORM",
        "checks": checks,
        "total_debt": total_debt,
    }


# ═══════════════════════════════════════════════════════════════════════
# 19.3  ENVIRONMENTAL COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════

async def environmental_compliance(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """Environmental regulation compliance check."""
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită"}

    # Environmental fines
    fines = (await db.execute(
        select(EnvironmentalFine)
        .where(EnvironmentalFine.company_id == company_id)
        .order_by(EnvironmentalFine.data_amenda.desc())
    )).scalars().all()

    total_fines = sum(float(f.suma or 0) for f in fines)
    recent_fines = [f for f in fines if f.data_amenda and (date.today() - f.data_amenda).days < 365]

    # High-risk CAEN for environmental
    industrial_caen = ["01", "02", "05", "06", "07", "08", "10", "11", "12",
                       "13", "14", "15", "16", "17", "19", "20", "21", "22",
                       "23", "24", "25", "35", "36", "37", "38", "39"]
    caen_prefix = (company.caen_principal or "00")[:2]
    is_industrial = caen_prefix in industrial_caen

    checks = []
    score = 100

    if len(fines) > 0:
        score -= min(30, len(fines) * 10)
        checks.append({
            "check": "AMENZI_MEDIU",
            "status": "FAIL" if len(fines) > 2 else "WARNING",
            "detail": f"{len(fines)} amenzi de mediu (total: {total_fines:,.0f} RON)",
        })

    if recent_fines:
        score -= 20
        checks.append({
            "check": "AMENZI_RECENTE",
            "status": "FAIL",
            "detail": f"{len(recent_fines)} amenzi în ultimele 12 luni",
        })

    if is_industrial:
        score -= 10
        checks.append({
            "check": "SECTOR_INDUSTRIAL",
            "status": "WARNING",
            "detail": f"CAEN {company.caen_principal}: sector cu impact ecologic potențial",
        })

    if not checks:
        checks.append({
            "check": "NO_ISSUES",
            "status": "PASS",
            "detail": "Nicio problemă de mediu identificată",
        })

    score = max(0, score)

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "environmental_score": score,
        "is_industrial_sector": is_industrial,
        "fines_count": len(fines),
        "total_fines_amount": total_fines,
        "recent_fines": len(recent_fines),
        "checks": checks,
    }


# ═══════════════════════════════════════════════════════════════════════
# 19.4  LABOR LAW COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════

async def labor_compliance(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """Employment/labor law compliance assessment."""
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită"}

    # Historical employee count
    fins = (await db.execute(
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.asc())
    )).scalars().all()

    checks = []
    score = 100

    if not fins:
        return {
            "company_id": company_id,
            "company_name": company.denumire,
            "labor_score": 50,
            "checks": [{"check": "NO_DATA", "status": "WARNING", "detail": "Fără date financiare"}],
        }

    latest = fins[-1]
    emp = latest.nr_angajati or 0

    # Large employer obligations
    if emp >= 50:
        checks.append({
            "check": "COMITET_SSM",
            "status": "INFO",
            "detail": f"Cu {emp} angajați — obligatoriu comitet SSM",
        })

    # Suspicious: high revenue, zero employees
    ca = float(latest.cifra_afaceri or 0)
    if ca > 1000000 and emp == 0:
        score -= 25
        checks.append({
            "check": "CA_FARA_ANGAJATI",
            "status": "WARNING",
            "detail": f"CA {ca:,.0f} RON cu 0 angajați — posibilă muncă fără contract",
        })

    # Employee trend
    if len(fins) >= 2:
        prev_emp = fins[-2].nr_angajati or 0
        if prev_emp > 0 and emp == 0:
            score -= 20
            checks.append({
                "check": "PIERDERE_TOTALA_ANGAJATI",
                "status": "FAIL",
                "detail": f"Toate posturile pierdute: de la {prev_emp} la {emp}",
            })
        elif prev_emp > 0 and emp < prev_emp * 0.5:
            score -= 10
            checks.append({
                "check": "REDUCERE_MASIVA",
                "status": "WARNING",
                "detail": f"Reducere angajați >50%: de la {prev_emp} la {emp}",
            })

    # Over-reliance on single administrator
    admin_count = (await db.execute(
        select(func.count()).select_from(CompanyPerson)
        .where(and_(
            CompanyPerson.company_id == company_id,
            CompanyPerson.tip == "ADMINISTRATOR",
            CompanyPerson.activ.is_(True),
        ))
    )).scalar() or 0

    if emp > 100 and admin_count <= 1:
        checks.append({
            "check": "MANAGEMENT_CONCENTRAT",
            "status": "INFO",
            "detail": f"{emp} angajați cu doar {admin_count} administrator activ",
        })

    if not checks:
        checks.append({
            "check": "OK",
            "status": "PASS",
            "detail": "Nicio problemă de dreptul muncii identificată",
        })

    score = max(0, score)

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "labor_score": score,
        "current_employees": emp,
        "checks": checks,
        "employee_history": [
            {"year": f.an_fiscal, "employees": f.nr_angajati or 0} for f in fins
        ],
    }


# ═══════════════════════════════════════════════════════════════════════
# 19.5  AML COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════

async def aml_compliance(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """Anti-money laundering risk assessment."""
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită"}

    risk_factors = []
    aml_score = 100

    # Young company
    if company.data_infiintare:
        age = (date.today() - company.data_infiintare).days / 365.25
        if age < 2:
            aml_score -= 15
            risk_factors.append({
                "factor": "FIRMA_TANARA",
                "risk": "MEDIUM",
                "detail": f"Înregistrată de {age:.1f} ani",
            })

    # Cash-intensive sectors
    cash_caen = ["47", "55", "56", "92", "93", "96"]
    caen_prefix = (company.caen_principal or "00")[:2]
    if caen_prefix in cash_caen:
        aml_score -= 10
        risk_factors.append({
            "factor": "SECTOR_CASH_INTENSIVE",
            "risk": "MEDIUM",
            "detail": f"CAEN {company.caen_principal}: sector cu tranzacții predominant cash",
        })

    # Frequent ownership changes
    total_associates = (await db.execute(
        select(func.count()).select_from(CompanyPerson)
        .where(and_(
            CompanyPerson.company_id == company_id,
            CompanyPerson.tip == "ASOCIAT",
        ))
    )).scalar() or 0

    active_associates = (await db.execute(
        select(func.count()).select_from(CompanyPerson)
        .where(and_(
            CompanyPerson.company_id == company_id,
            CompanyPerson.tip == "ASOCIAT",
            CompanyPerson.activ.is_(True),
        ))
    )).scalar() or 0

    if total_associates > 5 and active_associates <= 1:
        aml_score -= 15
        risk_factors.append({
            "factor": "SCHIMBARI_ACTIONARIAT",
            "risk": "HIGH",
            "detail": f"{total_associates} asociați total, doar {active_associates} activi",
        })

    # Fraud alerts
    fraud_count = (await db.execute(
        select(func.count()).select_from(FraudAlert)
        .where(FraudAlert.company_id == company_id)
    )).scalar() or 0
    if fraud_count > 0:
        aml_score -= 20
        risk_factors.append({
            "factor": "ALERTE_FRAUDA",
            "risk": "HIGH",
            "detail": f"{fraud_count} alerte de fraudă",
        })

    # Outstanding debts
    if company.has_debts:
        aml_score -= 10
        risk_factors.append({
            "factor": "DATORII_BUGET",
            "risk": "MEDIUM",
            "detail": "Datorii restante la bugetul de stat",
        })

    # Insolvency
    if company.has_insolvency:
        aml_score -= 15
        risk_factors.append({
            "factor": "INSOLVENTA",
            "risk": "HIGH",
            "detail": "Procedură de insolvență",
        })

    aml_score = max(0, aml_score)

    if aml_score >= 80:
        aml_level = "LOW_RISK"
    elif aml_score >= 50:
        aml_level = "MEDIUM_RISK"
    else:
        aml_level = "HIGH_RISK"

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "aml_score": aml_score,
        "aml_risk_level": aml_level,
        "risk_factors": risk_factors,
        "risk_factors_count": len(risk_factors),
        "recommendations": [
            "EDD (Enhanced Due Diligence) recomandat" if aml_level == "HIGH_RISK" else None,
            "Monitorizare tranzacții neobișnuite" if aml_level != "LOW_RISK" else None,
            "Verificare beneficiari reali" if total_associates > 3 else None,
            "Raportare tranzacții suspicioase" if fraud_count > 0 else None,
        ],
    }
