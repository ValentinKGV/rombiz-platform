"""
Relationship Intelligence endpoints — Branch 14.

Endpoints:
  GET  /relationships/ubo/{company_id}        — UBO discovery (14.1)
  GET  /relationships/contagion/{company_id}   — Contagion risk map (14.2)
  GET  /relationships/directors/{company_id}   — Shared directors network (14.3)
  GET  /relationships/group/{company_id}       — Corporate group detection (14.4)
  GET  /relationships/timeline/{company_id}    — Relationship timeline (14.5)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.relationship_intelligence import (
    discover_ubo,
    map_contagion_risk,
    shared_directors_network,
    detect_corporate_group,
    relationship_timeline,
)

router = APIRouter()


@router.get("/ubo/{company_id}", summary="Descoperiți Beneficiarul Real (UBO)")
async def get_ubo(
    company_id: int,
    threshold_pct: float = Query(25.0, ge=1.0, le=100.0),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await discover_ubo(db, company_id, threshold_pct)


@router.get("/contagion/{company_id}", summary="Mapare risc contagiune")
async def get_contagion_risk(
    company_id: int,
    max_depth: int = Query(3, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await map_contagion_risk(db, company_id, max_depth)


@router.get("/directors/{company_id}", summary="Rețea de directori comuni")
async def get_shared_directors(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await shared_directors_network(db, company_id)


@router.get("/group/{company_id}", summary="Detectare grup corporativ")
async def get_corporate_group(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await detect_corporate_group(db, company_id)


@router.get("/timeline/{company_id}", summary="Cronologie relații")
async def get_relationship_timeline(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await relationship_timeline(db, company_id)
