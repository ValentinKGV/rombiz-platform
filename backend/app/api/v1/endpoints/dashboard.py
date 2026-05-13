"""
Dashboard endpoints — overview stats, KPIs, widgets.

Branch 10 improvements:
  10.1: Date filters (period parameter)
  10.2: Extended widgets — ESG, fraud, exchange rates, contracts
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import (
    Company, FinancialData, RiskScore, ESGScore,
    Alert, ExchangeRate, PublicContract, CourtCase,
    CompanyDebt,
)

router = APIRouter()


def _period_start(period: str) -> date:
    """Convert period string to start date."""
    today = date.today()
    if period == "7d":
        return today - timedelta(days=7)
    elif period == "30d":
        return today - timedelta(days=30)
    elif period == "90d":
        return today - timedelta(days=90)
    elif period == "1y":
        return today - timedelta(days=365)
    elif period == "ytd":
        return date(today.year, 1, 1)
    return today - timedelta(days=30)  # default


@router.get("/stats")
async def dashboard_stats(
    period: str = Query(default="30d", pattern="^(7d|30d|90d|1y|ytd)$"),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Main dashboard statistics.
    10.1: Filterable by period.
    """
    # Basic company counts
    total = await db.execute(select(func.count(Company.id)))
    total_companies = total.scalar() or 0

    active = await db.execute(
        select(func.count(Company.id)).where(Company.stare == "ACTIVA")
    )
    total_active = active.scalar() or 0

    debts = await db.execute(
        select(func.count(Company.id)).where(Company.has_debts.is_(True))
    )
    total_with_debts = debts.scalar() or 0

    insolvent = await db.execute(
        select(func.count(Company.id)).where(Company.has_insolvency.is_(True))
    )
    total_insolvent = insolvent.scalar() or 0

    # Risk distribution
    risk_dist_result = await db.execute(
        select(RiskScore.rating, func.count(RiskScore.id))
        .group_by(RiskScore.rating)
    )
    risk_distribution = [
        {"category": row[0] or "N/A", "count": row[1]}
        for row in risk_dist_result.all()
    ]

    # Recent alerts (user-specific)
    period_start = _period_start(period)
    alerts_result = await db.execute(
        select(Alert)
        .where(Alert.user_id == user.sub)
        .order_by(Alert.created_at.desc())
        .limit(10)
    )
    recent_alerts = [
        {
            "id": a.id,
            "tip_alerta": a.tip_alerta,
            "titlu": a.titlu,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts_result.scalars().all()
    ]

    # Top sectors by CAEN
    sectors_result = await db.execute(
        select(Company.caen_principal, func.count(Company.id).label("cnt"))
        .where(Company.caen_principal.isnot(None))
        .group_by(Company.caen_principal)
        .order_by(func.count(Company.id).desc())
        .limit(10)
    )
    top_sectors = [
        {"caen": row[0], "name": row[0], "count": row[1]}
        for row in sectors_result.all()
    ]

    return {
        "total_companies": total_companies,
        "total_active": total_active,
        "total_with_debts": total_with_debts,
        "total_insolvent": total_insolvent,
        "risk_distribution": risk_distribution,
        "recent_alerts": recent_alerts,
        "top_sectors": top_sectors,
        "period": period,
    }


@router.get("/widgets/esg")
async def esg_widget(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """10.2: ESG overview widget — distribution by SFDR category."""
    sfdr_result = await db.execute(
        select(ESGScore.sfdr_categoria, func.count(ESGScore.id))
        .group_by(ESGScore.sfdr_categoria)
    )
    sfdr_distribution = [
        {"category": row[0] or "N/A", "count": row[1]}
        for row in sfdr_result.all()
    ]

    avg_result = await db.execute(
        select(
            func.avg(ESGScore.score_total),
            func.avg(ESGScore.score_e),
            func.avg(ESGScore.score_s),
            func.avg(ESGScore.score_g),
        )
    )
    avgs = avg_result.one()

    return {
        "sfdr_distribution": sfdr_distribution,
        "averages": {
            "total": round(float(avgs[0] or 0), 1),
            "e": round(float(avgs[1] or 0), 1),
            "s": round(float(avgs[2] or 0), 1),
            "g": round(float(avgs[3] or 0), 1),
        },
    }


@router.get("/widgets/fraud")
async def fraud_widget(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """10.2: Fraud overview — companies with debts or insolvency."""
    debt_count = await db.execute(
        select(func.count(Company.id)).where(Company.has_debts.is_(True))
    )
    insolvency_count = await db.execute(
        select(func.count(Company.id)).where(Company.has_insolvency.is_(True))
    )
    litigation_count = await db.execute(
        select(func.count(Company.id)).where(Company.has_litigation.is_(True))
    )

    return {
        "companies_with_debts": debt_count.scalar() or 0,
        "companies_with_insolvency": insolvency_count.scalar() or 0,
        "companies_with_litigation": litigation_count.scalar() or 0,
    }


@router.get("/widgets/exchange-rates")
async def exchange_rates_widget(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """10.2: Latest exchange rates from BNR."""
    # Get latest date
    latest_date = await db.execute(
        select(func.max(ExchangeRate.date))
    )
    max_date = latest_date.scalar()

    # Fallback: if DB has no rates or they're stale, fetch live from BNR
    from datetime import date as date_type
    if not max_date or max_date < date_type.today():
        try:
            from app.collectors.bnr import BNRCollector
            collector = BNRCollector()
            live_rates = await collector.fetch_all_rates()
            await collector.close()
            if live_rates:
                return {
                    "date": live_rates[0]["data_curs"],
                    "rates": [
                        {"currency": r["moneda"], "rate_ron": float(r["curs"])}
                        for r in live_rates
                    ],
                }
        except Exception:
            pass  # Fall through to DB data

    if not max_date:
        return {"rates": [], "date": None}

    result = await db.execute(
        select(ExchangeRate)
        .where(ExchangeRate.date == max_date)
        .order_by(ExchangeRate.currency)
    )
    rates = result.scalars().all()

    return {
        "date": str(max_date),
        "rates": [
            {"currency": r.currency, "rate_ron": float(r.rate_ron)}
            for r in rates
        ],
    }


@router.get("/widgets/contracts")
async def contracts_widget(
    period: str = Query(default="30d", pattern="^(7d|30d|90d|1y|ytd)$"),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """10.2: Public contracts overview."""
    period_start = _period_start(period)

    total_result = await db.execute(
        select(func.count(PublicContract.id), func.sum(PublicContract.valoare_ron))
    )
    total_row = total_result.one()

    recent_result = await db.execute(
        select(func.count(PublicContract.id), func.sum(PublicContract.valoare_ron))
        .where(PublicContract.data_atribuire >= period_start)
    )
    recent_row = recent_result.one()

    return {
        "total_contracts": total_row[0] or 0,
        "total_value": float(total_row[1] or 0),
        "recent_contracts": recent_row[0] or 0,
        "recent_value": float(recent_row[1] or 0),
        "period": period,
    }
