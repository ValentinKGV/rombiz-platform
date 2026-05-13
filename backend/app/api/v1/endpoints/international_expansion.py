"""
International Expansion endpoints — cross-border analysis, FX risk,
market entry scoring, regulatory comparison, and term translation.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.international_expansion import (
    cross_border_analysis,
    fx_risk_assessment,
    market_entry_scoring,
    regulatory_comparison,
    translate_business_terms,
)

router = APIRouter()


class TranslateBody(BaseModel):
    terms: list[str] | None = None
    target_language: str = "en"


@router.get("/cross-border/{company_id}")
async def cross_border(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await cross_border_analysis(db, company_id)


@router.get("/fx-risk/{company_id}")
async def fx_risk(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await fx_risk_assessment(db, company_id)


@router.get("/market-entry/{caen}")
async def market_entry(
    caen: str,
    target_country: str = Query("DE"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await market_entry_scoring(db, caen, target_country)


@router.get("/regulatory-comparison")
async def reg_comparison(
    countries: str = Query("RO,BG,HU,PL,DE"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    country_list = [c.strip() for c in countries.split(",")]
    return await regulatory_comparison(db, country_list)


@router.post("/translate")
async def translate(
    body: TranslateBody,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await translate_business_terms(db, body.terms, body.target_language)
