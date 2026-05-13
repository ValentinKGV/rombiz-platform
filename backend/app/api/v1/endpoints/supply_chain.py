"""
Supply Chain Risk endpoints — Branch 17.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.supply_chain import (
    discover_supplier_network,
    dependency_mapping,
    disruption_alerts,
    find_alternative_suppliers,
    supply_chain_score,
)

router = APIRouter()


@router.get("/network/{company_id}")
async def get_supplier_network(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """17.1 — Supplier network discovery."""
    return await discover_supplier_network(db, company_id)


@router.get("/dependencies/{company_id}")
async def get_dependencies(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """17.2 — Dependency mapping."""
    return await dependency_mapping(db, company_id)


@router.get("/disruptions/{company_id}")
async def get_disruptions(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """17.3 — Disruption alerts for supplier base."""
    return await disruption_alerts(db, company_id)


@router.get("/alternatives/{caen_code}")
async def get_alternatives(
    caen_code: str,
    judet: Optional[str] = None,
    limit: int = Query(15, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """17.4 — Find alternative suppliers."""
    return await find_alternative_suppliers(db, caen_code, judet, limit)


@router.get("/score/{company_id}")
async def get_supply_chain_score(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """17.5 — Supply chain risk score."""
    return await supply_chain_score(db, company_id)
