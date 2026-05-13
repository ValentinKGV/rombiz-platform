"""
Predictive Analytics endpoints — Branch 13.

Endpoints:
  GET  /predictive/forecast/{company_id}      — Financial forecasting (13.1)
  GET  /predictive/bankruptcy/{company_id}     — Bankruptcy probability (13.2)
  GET  /predictive/degradation/{company_id}    — Risk degradation prediction (13.3)
  GET  /predictive/sector/{caen_code}          — Sector trends (13.4)
  GET  /predictive/montecarlo/{portfolio_id}   — Monte Carlo simulation (13.5)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.schemas.schemas import (
    ForecastResponse,
    BankruptcyPrediction,
    RiskDegradationResponse,
    SectorTrendResponse,
    MonteCarloResponse,
)
from app.services.predictive_analytics import (
    forecast_financials,
    predict_bankruptcy,
    predict_risk_degradation,
    analyze_sector_trends,
    monte_carlo_portfolio,
)

router = APIRouter()


# ── 13.1  Financial Forecasting ──────────────────────────────────────

@router.get(
    "/forecast/{company_id}",
    response_model=ForecastResponse,
    summary="Predicție financiară",
    description="Proiecții lineare pe cifra de afaceri, profit, angajați (1-5 ani).",
)
async def get_forecast(
    company_id: int,
    years_ahead: int = Query(3, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await forecast_financials(db, company_id, years_ahead)


# ── 13.2  Bankruptcy Probability ─────────────────────────────────────

@router.get(
    "/bankruptcy/{company_id}",
    response_model=BankruptcyPrediction,
    summary="Probabilitate faliment",
    description="Model logistic de predicție insolvență bazat pe Z-Score, datorii, vechime, sector.",
)
async def get_bankruptcy_probability(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await predict_bankruptcy(db, company_id)


# ── 13.3  Risk Degradation Prediction ────────────────────────────────

@router.get(
    "/degradation/{company_id}",
    response_model=RiskDegradationResponse,
    summary="Predicție degradare risc",
    description="Analiză tendințe pentru predicția degradării scorului de risc în 6-12 luni.",
)
async def get_risk_degradation(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await predict_risk_degradation(db, company_id)


# ── 13.4  Sector Trends ──────────────────────────────────────────────

@router.get(
    "/sector/{caen_code}",
    response_model=SectorTrendResponse,
    summary="Trend sectorial",
    description="Analiză agregată la nivel de sector CAEN: creșteri/scăderi, nașteri/decese firme.",
)
async def get_sector_trends(
    caen_code: str,
    years: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await analyze_sector_trends(db, caen_code, years)


# ── 13.5  Monte Carlo Portfolio ───────────────────────────────────────

@router.get(
    "/montecarlo/{portfolio_id}",
    response_model=MonteCarloResponse,
    summary="Simulare Monte Carlo",
    description="1000 scenarii de simulare a riscului pe portofoliu (VaR 95/99, worst case).",
)
async def get_monte_carlo(
    portfolio_id: str,
    simulations: int = Query(1000, ge=100, le=10000),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_role("admin", "analyst")),
):
    return await monte_carlo_portfolio(db, portfolio_id, simulations)
