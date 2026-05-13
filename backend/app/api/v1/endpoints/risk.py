"""
Risk scoring endpoints — Altman Z-Score adapted for Romanian companies.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import Company, RiskScore, FinancialData
from app.schemas.schemas import RiskScoreSchema

router = APIRouter()


@router.get("/{cui}", response_model=RiskScoreSchema)
async def get_risk_score(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Get latest risk score for a company.
    Score components:
      - financial (Altman Z-Score adapted) — 30%
      - legal (court cases, insolvency) — 25%
      - fiscal (debts, TVA status) — 25%
      - behavioral (payment history) — 20%
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = await db.execute(
        select(RiskScore)
        .where(RiskScore.company_id == company.id)
        .order_by(RiskScore.calculat_la.desc())
        .limit(1)
    )
    risk = result.scalar_one_or_none()
    if not risk:
        raise HTTPException(status_code=404, detail="No risk score available. Trigger recalculation.")

    return RiskScoreSchema.model_validate(risk)


@router.post("/{cui}/recalculate")
async def recalculate_risk_score(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Trigger async recalculation of risk score.
    Dispatches a Celery task.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Import here to avoid circular import with Celery
    from app.tasks.risk_tasks import recalculate_risk_score_task
    task = recalculate_risk_score_task.delay(company.id)

    return {"status": "queued", "task_id": str(task.id)}


@router.get("/{cui}/history")
async def get_risk_history(
    cui: int,
    limit: int = Query(default=12, le=60),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Get risk score history for trend analysis.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = await db.execute(
        select(RiskScore)
        .where(RiskScore.company_id == company.id)
        .order_by(RiskScore.calculat_la.desc())
        .limit(limit)
    )
    scores = result.scalars().all()
    return [
        {
            "score": float(s.score),
            "rating": s.rating,
            "scor_financiar": float(s.scor_financiar) if s.scor_financiar else None,
            "scor_legal": float(s.scor_legal) if s.scor_legal else None,
            "scor_fiscal": float(s.scor_fiscal) if s.scor_fiscal else None,
            "scor_comportamental": float(s.scor_comportamental) if s.scor_comportamental else None,
            "calculat_la": s.calculat_la,
        }
        for s in scores
    ]


@router.get("/distribution/by-sector")
async def risk_distribution_by_sector(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Aggregate risk distribution grouped by CAEN sector.
    """
    result = await db.execute(
        select(
            func.substr(Company.caen_principal, 1, 2).label("sector"),
            func.avg(RiskScore.score).label("avg_risk"),
            func.count().label("count"),
        )
        .join(RiskScore, RiskScore.company_id == Company.id)
        .group_by(func.substr(Company.caen_principal, 1, 2))
        .order_by(func.avg(RiskScore.score).desc())
        .limit(20)
    )
    return [
        {
            "sector_caen": r.sector,
            "avg_risk_score": round(float(r.avg_risk), 2),
            "company_count": r.count,
        }
        for r in result.all()
    ]


@router.get("/{cui}/predict")
async def predict_risk_trend(
    cui: int,
    months: int = Query(default=6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Predict future risk score trend using linear regression on historical scores.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    from app.services.risk_scoring import RiskScoringEngine
    engine = RiskScoringEngine(db)
    prediction = await engine.predict_trend(company.id, months_ahead=months)
    return prediction


@router.get("/benchmark/sector")
async def sector_benchmark(
    caen: str = Query(..., min_length=2, max_length=2, description="CAEN 2-digit sector code"),
    judet: str | None = Query(default=None, description="Filter by county"),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Get risk benchmark for a CAEN sector: average, median, distribution, top/bottom 5.
    """
    from app.services.risk_scoring import RiskScoringEngine
    engine = RiskScoringEngine(db)
    benchmark = await engine.get_sector_benchmark(caen, judet=judet)
    return benchmark
