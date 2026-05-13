"""
New Companies Feed endpoints — daily feed of newly registered companies.
"""
from __future__ import annotations

from typing import Optional
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import NewCompanyFeed, Company

router = APIRouter()


@router.get("")
async def list_new_companies(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, le=200, alias="page_size"),
    data_de_la: Optional[date] = None,
    data_pana_la: Optional[date] = None,
    judet: Optional[str] = None,
    cod_caen: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    List newly registered companies.
    Default: last 7 days.
    """
    if not data_de_la:
        data_de_la = date.today() - timedelta(days=30)
    if not data_pana_la:
        data_pana_la = date.today()

    base_filter = and_(
        NewCompanyFeed.registration_date >= data_de_la,
        NewCompanyFeed.registration_date <= data_pana_la,
    )

    count_query = (
        select(func.count(NewCompanyFeed.id))
        .join(Company, NewCompanyFeed.company_id == Company.id)
        .where(base_filter)
    )
    if judet:
        count_query = count_query.where(Company.judet == judet)
    if cod_caen:
        count_query = count_query.where(Company.caen_principal == cod_caen)
    total = (await db.execute(count_query)).scalar() or 0

    query = (
        select(NewCompanyFeed)
        .options(joinedload(NewCompanyFeed.company))
        .join(Company, NewCompanyFeed.company_id == Company.id)
        .where(base_filter)
    )

    if judet:
        query = query.where(Company.judet == judet)
    if cod_caen:
        query = query.where(Company.caen_principal == cod_caen)

    offset = (page - 1) * per_page
    query = query.order_by(NewCompanyFeed.registration_date.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    entries = result.unique().scalars().all()

    return {
        "items": [
            {
                "id": e.id,
                "cui": e.company.cui if e.company else None,
                "denumire": e.company.denumire if e.company else None,
                "caen_principal": e.company.caen_principal if e.company else None,
                "cod_caen": e.company.caen_principal if e.company else None,
                "judet": e.company.judet if e.company else None,
                "localitate": e.company.localitate if e.company else None,
                "registration_date": e.registration_date,
                "data_inregistrare": e.registration_date,
                "capital_social": float(e.company.capital_social) if e.company and e.company.capital_social else None,
                "forma_juridica": e.company.forma_juridica if e.company else None,
            }
            for e in entries
        ],
        "total": total,
        "page": page,
        "page_size": per_page,
    }


@router.get("/stats")
async def new_companies_stats(
    days: int = Query(default=30, le=365),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Statistics on new company registrations.
    """
    since = date.today() - timedelta(days=days)

    # Total count
    total = await db.execute(
        select(func.count(NewCompanyFeed.id))
        .where(NewCompanyFeed.registration_date >= since)
    )

    # By county (via join)
    by_judet = await db.execute(
        select(
            Company.judet,
            func.count().label("cnt"),
        )
        .join(NewCompanyFeed, NewCompanyFeed.company_id == Company.id)
        .where(NewCompanyFeed.registration_date >= since)
        .group_by(Company.judet)
        .order_by(func.count().desc())
        .limit(42)
    )

    # By CAEN sector (top 20, via join)
    by_caen = await db.execute(
        select(
            func.substr(Company.caen_principal, 1, 2).label("sector"),
            func.count().label("cnt"),
        )
        .join(NewCompanyFeed, NewCompanyFeed.company_id == Company.id)
        .where(NewCompanyFeed.registration_date >= since)
        .group_by(func.substr(Company.caen_principal, 1, 2))
        .order_by(func.count().desc())
        .limit(20)
    )

    # Daily trend
    daily = await db.execute(
        select(
            NewCompanyFeed.registration_date,
            func.count().label("cnt"),
        )
        .where(NewCompanyFeed.registration_date >= since)
        .group_by(NewCompanyFeed.registration_date)
        .order_by(NewCompanyFeed.registration_date)
    )

    by_judet_data = [
        {"judet": r.judet, "count": r.cnt}
        for r in by_judet.all()
    ]

    return {
        "period_days": days,
        "total": total.scalar() or 0,
        "today": (await db.execute(
            select(func.count(NewCompanyFeed.id))
            .where(NewCompanyFeed.registration_date == date.today())
        )).scalar() or 0,
        "this_week": (await db.execute(
            select(func.count(NewCompanyFeed.id))
            .where(NewCompanyFeed.registration_date >= date.today() - timedelta(days=date.today().weekday()))
        )).scalar() or 0,
        "this_month": (await db.execute(
            select(func.count(NewCompanyFeed.id))
            .where(NewCompanyFeed.registration_date >= date.today().replace(day=1))
        )).scalar() or 0,
        "by_judet": by_judet_data,
        "by_county": by_judet_data,
        "by_caen_sector": [
            {"sector": r.sector, "count": r.cnt}
            for r in by_caen.all()
        ],
        "daily_trend": [
            {"date": r.registration_date.isoformat(), "count": r.cnt}
            for r in daily.all()
        ],
    }


@router.get("/heatmap")
async def new_companies_heatmap(
    days: int = Query(default=30, le=365),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Geographic heatmap data for new company registrations.
    Returns county-level data for Leaflet.js visualization.
    """
    since = date.today() - timedelta(days=days)

    result = await db.execute(
        select(
            Company.judet,
            func.count().label("cnt"),
            func.avg(Company.capital_social).label("avg_capital"),
        )
        .join(NewCompanyFeed, NewCompanyFeed.company_id == Company.id)
        .where(NewCompanyFeed.registration_date >= since)
        .group_by(Company.judet)
    )

    return [
        {
            "judet": r.judet,
            "count": r.cnt,
            "avg_capital": round(float(r.avg_capital), 2) if r.avg_capital else None,
        }
        for r in result.all()
    ]
