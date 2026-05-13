"""
ESG Scoring endpoints — Environmental, Social, Governance.
All scores include mandatory source citation and disclaimer.

v2 Endpoints:
  - GET  /{cui}                 → latest ESG score
  - POST /{cui}/recalculate     → trigger recalculation
  - GET  /{cui}/raw-data        → raw data points
  - GET  /{cui}/environmental-fines → env fines
  - GET  /{cui}/factsheet       → ESG factsheet (2.5)
  - GET  /{cui}/timeline        → ESG score timeline (2.5)
  - POST /compare               → compare multiple companies (2.5)
  - POST /portfolio/aggregate   → portfolio ESG aggregate (2.5)
  - GET  /ranking/top           → ranking
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import Company, ESGScore, ESGRawData, EnvironmentalFine
from app.schemas.schemas import ESGScoreSchema
from app.services.esg_scoring import ESGScoringEngine

router = APIRouter()

ESG_DISCLAIMER = (
    "Scorul ESG este generat automat pe baza datelor publice disponibile. "
    "Nu constituie o evaluare oficială sau un rating de credit. "
    "Sursele sunt citate pentru fiecare componentă."
)


@router.get("/{cui}", response_model=ESGScoreSchema)
async def get_esg_score(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Get latest ESG composite score with E/S/G sub-scores.
    Hard constraint #12: all scores include cited sources + disclaimer.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = await db.execute(
        select(ESGScore)
        .where(ESGScore.company_id == company.id)
        .order_by(ESGScore.calculat_la.desc())
        .limit(1)
    )
    esg = result.scalar_one_or_none()
    if not esg:
        raise HTTPException(status_code=404, detail="No ESG score available")

    return ESGScoreSchema.model_validate(esg)


@router.post("/{cui}/recalculate")
async def recalculate_esg_score(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Trigger async ESG score recalculation via Celery.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    from app.tasks.esg_tasks import recalculate_esg_score_task
    task = recalculate_esg_score_task.delay(company.id)

    return {"status": "queued", "task_id": str(task.id)}


@router.get("/{cui}/raw-data")
async def get_esg_raw_data(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Get raw ESG data points used in scoring (for transparency).
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = await db.execute(
        select(ESGRawData)
        .where(ESGRawData.company_id == company.id)
        .order_by(ESGRawData.data_colectare.desc())
        .limit(50)
    )
    data_points = result.scalars().all()
    return [
        {
            "sursa": d.sursa,
            "indicator": d.indicator,
            "categorie": d.categorie,
            "valoare": d.valoare,
            "data_colectare": d.data_colectare,
        }
        for d in data_points
    ]


@router.get("/{cui}/environmental-fines")
async def get_environmental_fines(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Get environmental fines from GNM/APM.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = await db.execute(
        select(EnvironmentalFine)
        .where(EnvironmentalFine.company_id == company.id)
        .order_by(EnvironmentalFine.data_amenda.desc())
    )
    fines = result.scalars().all()
    return [
        {
            "autoritate": f.autoritate,
            "motiv": f.motiv,
            "suma_ron": float(f.suma_ron) if f.suma_ron else None,
            "data_amenda": f.data_amenda,
            "status": f.status,
        }
        for f in fines
    ]


@router.get("/ranking/top")
async def esg_ranking(
    limit: int = Query(default=50, le=200),
    sector: str = Query(default=None, description="CAEN 2-digit sector code"),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Top companies by ESG composite score.
    """
    query = (
        select(
            Company.cui,
            Company.denumire,
            Company.caen_principal,
            ESGScore.score_total,
            ESGScore.score_e,
            ESGScore.score_s,
            ESGScore.score_g,
        )
        .join(ESGScore, ESGScore.company_id == Company.id)
    )

    if sector:
        query = query.where(Company.caen_principal.startswith(sector))

    query = query.order_by(ESGScore.score_total.desc()).limit(limit)
    result = await db.execute(query)

    return {
        "disclaimer": ESG_DISCLAIMER,
        "ranking": [
            {
                "cui": r.cui,
                "denumire": r.denumire,
                "caen_principal": r.caen_principal,
                "score_total": float(r.score_total) if r.score_total else None,
                "score_e": float(r.score_e) if r.score_e else None,
                "score_s": float(r.score_s) if r.score_s else None,
                "score_g": float(r.score_g) if r.score_g else None,
            }
            for r in result.all()
        ],
    }


# ──────────────────────────────────────────────────────────────────
# 2.5: NEW ENDPOINTS — Factsheet, Compare, Portfolio, Timeline
# ──────────────────────────────────────────────────────────────────

@router.get("/{cui}/factsheet")
async def get_esg_factsheet(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    2.5: ESG factsheet data for a single company.
    Returns structured data suitable for PDF generation or display.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    engine = ESGScoringEngine(db)
    try:
        factsheet = await engine.get_factsheet(company.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return factsheet


@router.get("/{cui}/timeline")
async def get_esg_timeline(
    cui: int,
    limit: int = Query(default=12, le=50),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    2.5: ESG score history timeline for trend visualization.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    engine = ESGScoringEngine(db)
    timeline = await engine.get_timeline(company.id, limit=limit)

    return {
        "cui": cui,
        "denumire": company.denumire,
        "timeline": timeline,
        "disclaimer": ESG_DISCLAIMER,
    }


@router.post("/compare")
async def compare_esg_scores(
    company_cuis: list[int] = Body(..., min_length=2, max_length=10),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    2.5: Compare ESG scores of multiple companies side-by-side.
    POST body: list of CUI numbers [12345678, 87654321, ...]
    """
    # Resolve CUIs to company IDs
    result = await db.execute(
        select(Company.id, Company.cui).where(Company.cui.in_(company_cuis))
    )
    companies = result.all()

    if not companies:
        raise HTTPException(status_code=404, detail="No companies found")

    company_ids = [c[0] for c in companies]

    engine = ESGScoringEngine(db)
    comparison = await engine.compare_companies(company_ids)

    return {
        "comparison": comparison,
        "disclaimer": ESG_DISCLAIMER,
    }


@router.post("/portfolio/aggregate")
async def portfolio_esg_aggregate(
    company_cuis: list[int] = Body(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    2.5: Compute weighted average ESG score for a portfolio.
    POST body: list of CUI numbers
    """
    result = await db.execute(
        select(Company.id).where(Company.cui.in_(company_cuis))
    )
    company_ids = [r for r in result.scalars().all()]

    if not company_ids:
        raise HTTPException(status_code=404, detail="No companies found")

    engine = ESGScoringEngine(db)
    aggregate = await engine.portfolio_aggregate(company_ids)

    return aggregate
