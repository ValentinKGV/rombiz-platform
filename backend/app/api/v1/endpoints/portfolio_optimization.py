"""
Portfolio Optimization endpoints — optimization, rebalancing,
benchmarks, attribution, and scenario planning.
"""
import uuid as uuid_mod
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.portfolio_optimization import (
    optimize_portfolio,
    rebalance_portfolio,
    benchmark_tracking,
    attribution_analysis,
    scenario_planning,
)

router = APIRouter()


def _to_uuid(val: str) -> uuid_mod.UUID:
    return uuid_mod.UUID(val) if not isinstance(val, uuid_mod.UUID) else val


@router.get("/optimize/{portfolio_id}")
async def optimize(
    portfolio_id: str,
    risk_tolerance: str = Query("moderate", pattern="^(conservative|moderate|aggressive)$"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await optimize_portfolio(db, _to_uuid(portfolio_id), risk_tolerance)


@router.get("/rebalance/{portfolio_id}")
async def rebalance(
    portfolio_id: str,
    strategy: str = Query("risk_parity", pattern="^(risk_parity|equal_weight|momentum)$"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await rebalance_portfolio(db, _to_uuid(portfolio_id), strategy)


@router.get("/benchmark/{portfolio_id}")
async def benchmark(
    portfolio_id: str,
    benchmark: str = Query("market"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await benchmark_tracking(db, _to_uuid(portfolio_id), benchmark)


@router.get("/attribution/{portfolio_id}")
async def attribution(
    portfolio_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await attribution_analysis(db, _to_uuid(portfolio_id))


@router.get("/scenarios/{portfolio_id}")
async def scenarios(
    portfolio_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await scenario_planning(db, _to_uuid(portfolio_id))
