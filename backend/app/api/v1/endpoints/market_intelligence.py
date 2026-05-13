"""
Market Intelligence endpoints — Branch 16.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import StatisticSnapshot
from app.services.market_intelligence import (
    competitive_analysis,
    sector_benchmarks,
    market_sizing,
    ma_target_screening,
    price_intelligence,
)

router = APIRouter()


@router.get("/competitors/{company_id}")
async def get_competitors(
    company_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """16.1 — Competitive analysis."""
    return await competitive_analysis(db, company_id, limit)


@router.get("/benchmarks/{caen_code}")
async def get_benchmarks(
    caen_code: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """16.2 — Sector benchmarks."""
    return await sector_benchmarks(db, caen_code)


@router.get("/market-size/{caen_code}")
async def get_market_size(
    caen_code: str,
    judet: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """16.3 — Market sizing."""
    return await market_sizing(db, caen_code, judet)


@router.get("/ma-targets/{caen_code}")
async def get_ma_targets(
    caen_code: str,
    min_ca: float = Query(0),
    max_ca: float = Query(100_000_000),
    min_margin: float = Query(0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """16.4 — M&A target screening."""
    return await ma_target_screening(db, caen_code, min_ca, max_ca, min_margin, limit)


@router.get("/price-intelligence/{company_id}")
async def get_price_intelligence(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """16.5 — Price intelligence / productivity metrics."""
    return await price_intelligence(db, company_id)


@router.get("/macro-indicators")
async def get_macro_indicators(
    category: Optional[str] = Query(None, description="Filter by category: gdp, inflation, unemployment, etc."),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """16.6 — INS macroeconomic indicators (GDP, inflation, unemployment, etc.)."""
    query = select(StatisticSnapshot).order_by(desc(StatisticSnapshot.fetched_at))
    if category:
        query = query.where(StatisticSnapshot.category == category)
    query = query.limit(limit)
    result = await db.execute(query)
    snapshots = result.scalars().all()
    return [
        {
            "indicator_code": s.indicator_code,
            "indicator_name": s.indicator_name,
            "category": s.category,
            "period": s.period,
            "measure_unit": s.measure_unit,
            "data": s.value_json,
            "fetched_at": s.fetched_at,
        }
        for s in snapshots
    ]
