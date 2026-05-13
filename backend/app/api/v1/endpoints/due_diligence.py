"""
Due Diligence endpoints — Branch 15.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.due_diligence import (
    generate_dd_checklist,
    detect_red_flags,
    compare_peers,
    generate_dd_report,
    compliance_scoring,
)

router = APIRouter()


@router.get("/checklist/{company_id}")
async def dd_checklist(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """15.1 — Automated due diligence checklist."""
    return await generate_dd_checklist(db, company_id)


@router.get("/redflags/{company_id}")
async def dd_red_flags(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """15.2 — Red flag detection."""
    return await detect_red_flags(db, company_id)


@router.get("/peers/{company_id}")
async def dd_peers(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """15.3 — Peer comparison analysis."""
    return await compare_peers(db, company_id)


@router.get("/report/{company_id}")
async def dd_report(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """15.4 — Full due diligence report."""
    return await generate_dd_report(db, company_id)


@router.get("/compliance/{company_id}")
async def dd_compliance(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """15.5 — KYC/AML compliance scoring."""
    return await compliance_scoring(db, company_id)
