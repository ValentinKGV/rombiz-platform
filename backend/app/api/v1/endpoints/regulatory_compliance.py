"""
Regulatory Compliance endpoints — Branch 19.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.regulatory_compliance import (
    gdpr_compliance_check,
    fiscal_compliance,
    environmental_compliance,
    labor_compliance,
    aml_compliance,
)

router = APIRouter()


@router.get("/gdpr/{company_id}")
async def get_gdpr_compliance(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """19.1 — GDPR compliance check."""
    return await gdpr_compliance_check(db, company_id)


@router.get("/fiscal/{company_id}")
async def get_fiscal_compliance(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """19.2 — Fiscal compliance."""
    return await fiscal_compliance(db, company_id)


@router.get("/environmental/{company_id}")
async def get_environmental_compliance(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """19.3 — Environmental compliance."""
    return await environmental_compliance(db, company_id)


@router.get("/labor/{company_id}")
async def get_labor_compliance(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """19.4 — Labor law compliance."""
    return await labor_compliance(db, company_id)


@router.get("/aml/{company_id}")
async def get_aml_compliance(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """19.5 — AML compliance."""
    return await aml_compliance(db, company_id)
