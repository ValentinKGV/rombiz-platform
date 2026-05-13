"""
AI Anomaly Detection — Celery periodic task.
Scans companies for financial anomalies and generates smart alerts.
Runs without Claude API — uses rule-based pattern detection.
"""
import asyncio
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.celery_app import celery_app
from app.core.database import get_db_context
from app.core.logging import get_logger

logger = get_logger(__name__)

# Anomaly detection thresholds
THRESHOLDS = {
    "revenue_drop_pct": -30,        # CA drop > 30%
    "revenue_spike_pct": 100,       # CA spike > 100%
    "profit_to_loss": True,         # Switched from profit to loss
    "debt_ratio_critical": 0.85,    # Grad îndatorare > 85%
    "liquidity_critical": 0.5,      # Rata lichiditate < 0.5
    "employee_drop_pct": -50,       # Lost >50% employees
    "risk_downgrade_levels": 2,     # Risk rating dropped 2+ levels
}

RATING_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}


@celery_app.task(name="app.tasks.ai_anomaly_tasks.detect_anomalies")
def detect_anomalies():
    """Scan active companies for financial anomalies and create alerts."""
    return asyncio.run(_detect_anomalies())


async def _detect_anomalies():
    from app.models.models import (
        Company, FinancialData, RiskScore,
        MonitoredPortfolio, PortfolioCompany,
    )

    anomalies_found = 0
    alerts_created = 0

    async with get_db_context() as db:
        from app.services.alerts_service import AlertsService
        alerts_svc = AlertsService(db)

        # Get companies that are in at least one portfolio (monitored)
        monitored = await db.execute(
            select(Company.id, Company.cui, Company.denumire)
            .join(PortfolioCompany, PortfolioCompany.company_id == Company.id)
            .where(Company.stare == "ACTIVA")
            .distinct()
        )
        companies = monitored.all()

        if not companies:
            # Fallback: scan all active companies (limit 500)
            result = await db.execute(
                select(Company.id, Company.cui, Company.denumire)
                .where(Company.stare == "ACTIVA")
                .limit(500)
            )
            companies = result.all()

        logger.info(f"AI Anomaly scan: checking {len(companies)} companies")

        for comp in companies:
            company_id, cui, denumire = comp.id, comp.cui, comp.denumire

            try:
                anomalies = await _check_company_anomalies(db, company_id, cui, denumire)

                for anomaly in anomalies:
                    anomalies_found += 1

                    created = await alerts_svc.create_alert(
                        company_id=company_id,
                        tip_alerta="ai_anomaly_detected",
                        mesaj=f"[{anomaly['code']}] {anomaly['message']}",
                        detalii={
                            "anomaly_type": anomaly["code"],
                            "description": anomaly["message"],
                            "details": anomaly.get("details", {}),
                            "ai_generated": True,
                        },
                        severity=anomaly["severity"],
                    )
                    alerts_created += len(created)

            except Exception as e:
                logger.warning(f"Anomaly check failed for CUI {cui}: {e}")
                continue

        await db.commit()

    logger.info(f"AI Anomaly scan complete: {anomalies_found} anomalies, {alerts_created} alerts created")
    return {"anomalies_found": anomalies_found, "alerts_created": alerts_created}


async def _check_company_anomalies(
    db: AsyncSession, company_id: int, cui: int, denumire: str
) -> list[dict]:
    """Check a single company for anomalies. Returns list of anomaly dicts."""
    from app.models.models import FinancialData, RiskScore

    anomalies = []

    # Get last 2 years of financials
    result = await db.execute(
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.desc())
        .limit(2)
    )
    financials = result.scalars().all()

    if len(financials) >= 2:
        latest, prev = financials[0], financials[1]

        # Revenue drop/spike
        if prev.cifra_afaceri and prev.cifra_afaceri > 0 and latest.cifra_afaceri is not None:
            ca_change = float((latest.cifra_afaceri - prev.cifra_afaceri) / prev.cifra_afaceri * 100)
            if ca_change <= THRESHOLDS["revenue_drop_pct"]:
                anomalies.append({
                    "code": "REVENUE_DROP",
                    "severity": "ridicat",
                    "message": f"{denumire} (CUI {cui}): cifra de afaceri a scăzut cu {abs(ca_change):.0f}% "
                               f"(de la {float(prev.cifra_afaceri):,.0f} la {float(latest.cifra_afaceri):,.0f} RON)",
                    "details": {"pct_change": round(ca_change, 1), "year": latest.an_fiscal},
                })
            elif ca_change >= THRESHOLDS["revenue_spike_pct"]:
                anomalies.append({
                    "code": "REVENUE_SPIKE",
                    "severity": "mediu",
                    "message": f"{denumire} (CUI {cui}): creștere neobișnuită a CA cu {ca_change:.0f}% "
                               f"(de la {float(prev.cifra_afaceri):,.0f} la {float(latest.cifra_afaceri):,.0f} RON)",
                    "details": {"pct_change": round(ca_change, 1), "year": latest.an_fiscal},
                })

        # Profit to loss
        if prev.profit_net and prev.profit_net > 0 and latest.profit_net and latest.profit_net < 0:
            anomalies.append({
                "code": "PROFIT_TO_LOSS",
                "severity": "ridicat",
                "message": f"{denumire} (CUI {cui}): a trecut pe pierdere — "
                           f"de la +{float(prev.profit_net):,.0f} la {float(latest.profit_net):,.0f} RON",
                "details": {"prev_profit": float(prev.profit_net), "curr_profit": float(latest.profit_net)},
            })

        # Critical debt ratio
        if latest.grad_indatorare and float(latest.grad_indatorare) > THRESHOLDS["debt_ratio_critical"]:
            anomalies.append({
                "code": "DEBT_RATIO_CRITICAL",
                "severity": "critic",
                "message": f"{denumire} (CUI {cui}): grad de îndatorare critic — "
                           f"{float(latest.grad_indatorare) * 100:.1f}%",
                "details": {"debt_ratio": float(latest.grad_indatorare)},
            })

        # Critical liquidity
        if latest.rata_lichiditate and float(latest.rata_lichiditate) < THRESHOLDS["liquidity_critical"]:
            anomalies.append({
                "code": "LIQUIDITY_CRITICAL",
                "severity": "ridicat",
                "message": f"{denumire} (CUI {cui}): lichiditate critică — "
                           f"rata {float(latest.rata_lichiditate):.2f}",
                "details": {"liquidity_ratio": float(latest.rata_lichiditate)},
            })

        # Employee drop
        if prev.nr_angajati and prev.nr_angajati > 5 and latest.nr_angajati is not None:
            emp_change = (latest.nr_angajati - prev.nr_angajati) / prev.nr_angajati * 100
            if emp_change <= THRESHOLDS["employee_drop_pct"]:
                anomalies.append({
                    "code": "EMPLOYEE_DROP",
                    "severity": "mediu",
                    "message": f"{denumire} (CUI {cui}): reducere masivă personal — "
                               f"de la {prev.nr_angajati} la {latest.nr_angajati} angajați ({emp_change:.0f}%)",
                    "details": {"prev_count": prev.nr_angajati, "curr_count": latest.nr_angajati},
                })

    # Risk rating downgrade
    risk_result = await db.execute(
        select(RiskScore)
        .where(RiskScore.company_id == company_id)
        .order_by(RiskScore.calculat_la.desc())
        .limit(2)
    )
    risks = risk_result.scalars().all()

    if len(risks) >= 2:
        latest_risk, prev_risk = risks[0], risks[1]
        if latest_risk.rating and prev_risk.rating:
            curr_level = RATING_ORDER.get(latest_risk.rating, 0)
            prev_level = RATING_ORDER.get(prev_risk.rating, 0)
            if prev_level - curr_level >= THRESHOLDS["risk_downgrade_levels"]:
                anomalies.append({
                    "code": "RISK_DOWNGRADE",
                    "severity": "critic",
                    "message": f"{denumire} (CUI {cui}): degradare risc de la "
                               f"{prev_risk.rating} la {latest_risk.rating} "
                               f"(scor: {float(latest_risk.score):.0f}/100)",
                    "details": {
                        "prev_rating": prev_risk.rating,
                        "curr_rating": latest_risk.rating,
                        "score": float(latest_risk.score),
                    },
                })

    return anomalies
