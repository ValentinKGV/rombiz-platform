"""
SEAP (Public Procurement) endpoints — active tenders, contracts, statistics.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import PublicContract, PublicTenderActive, Company
from app.schemas.schemas import TenderSchema

router = APIRouter()


@router.get("/tenders")
async def list_active_tenders(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, le=100, alias="page_size"),
    q: Optional[str] = None,
    cpv: Optional[str] = None,
    cod_cpv: Optional[str] = None,
    autoritate: Optional[str] = None,
    valoare_min: Optional[float] = None,
    valoare_max: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    List active public tenders from SEAP.
    """
    query = select(PublicTenderActive)

    cpv_filter = cpv or cod_cpv
    filters = []
    if q:
        filters.append(PublicTenderActive.title.ilike(f"%{q}%"))
    if cpv_filter:
        filters.append(PublicTenderActive.cpv_code.startswith(cpv_filter))
    if autoritate:
        filters.append(PublicTenderActive.authority_name.ilike(f"%{autoritate}%"))
    if valoare_min is not None:
        filters.append(PublicTenderActive.estimated_value >= valoare_min)
    if valoare_max is not None:
        filters.append(PublicTenderActive.estimated_value <= valoare_max)

    if filters:
        query = query.where(and_(*filters))

    offset = (page - 1) * per_page
    query = query.order_by(PublicTenderActive.submission_deadline.asc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    items = []
    for t in result.scalars().all():
        d = TenderSchema.model_validate(t).model_dump()
        d["stare"] = "ACTIVA"
        d["titlu"] = d.get("title")
        items.append(d)
    return {"items": items}


@router.get("/tenders/{tender_id}")
async def get_tender_detail(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get detailed tender information."""
    result = await db.execute(
        select(PublicTenderActive).where(PublicTenderActive.id == tender_id)
    )
    tender = result.scalar_one_or_none()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    return TenderSchema.model_validate(tender)


@router.get("/contracts")
async def list_contracts(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, le=100),
    autoritate: Optional[str] = None,
    furnizor_cui: Optional[int] = None,
    cod_cpv: Optional[str] = None,
    data_de_la: Optional[date] = None,
    data_pana_la: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Search awarded public contracts.
    """
    query = select(PublicContract)
    filters = []

    if autoritate:
        filters.append(PublicContract.autoritate_contractanta.ilike(f"%{autoritate}%"))
    if furnizor_cui:
        subq = select(Company.id).where(Company.cui == furnizor_cui)
        filters.append(PublicContract.company_id.in_(subq))
    if cod_cpv:
        filters.append(PublicContract.cod_cpv.startswith(cod_cpv))
    if data_de_la:
        filters.append(PublicContract.data_atribuire >= data_de_la)
    if data_pana_la:
        filters.append(PublicContract.data_atribuire <= data_pana_la)

    if filters:
        query = query.where(and_(*filters))

    offset = (page - 1) * per_page
    query = query.order_by(PublicContract.data_atribuire.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    contracts = result.scalars().all()

    return [
        {
            "id": c.id,
            "nr_contract": c.nr_contract,
            "autoritate_contractanta": c.autoritate_contractanta,
            "titlu_contract": c.titlu_contract,
            "valoare_ron": float(c.valoare_ron) if c.valoare_ron else None,
            "data_atribuire": c.data_atribuire,
            "cod_cpv": c.cod_cpv,
        }
        for c in contracts
    ]


@router.get("/stats/by-authority")
async def contracts_by_authority(
    top: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Top contracting authorities by total awarded value.
    """
    result = await db.execute(
        select(
            PublicContract.autoritate_contractanta,
            func.count().label("nr_contracte"),
            func.sum(PublicContract.valoare_ron).label("total_ron"),
        )
        .group_by(PublicContract.autoritate_contractanta)
        .order_by(func.sum(PublicContract.valoare_ron).desc())
        .limit(top)
    )
    return [
        {
            "autoritate": r.autoritate_contractanta,
            "nr_contracte": r.nr_contracte,
            "total_ron": float(r.total_ron) if r.total_ron else 0,
        }
        for r in result.all()
    ]


@router.get("/stats/by-cpv")
async def contracts_by_cpv(
    top: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Contract distribution by CPV code.
    """
    result = await db.execute(
        select(
            PublicContract.cod_cpv,
            func.count().label("nr_contracte"),
            func.sum(PublicContract.valoare_ron).label("total_ron"),
        )
        .where(PublicContract.cod_cpv.isnot(None))
        .group_by(PublicContract.cod_cpv)
        .order_by(func.sum(PublicContract.valoare_ron).desc())
        .limit(top)
    )
    return {"items": [
        {
            "cpv": r.cod_cpv,
            "cod_cpv": r.cod_cpv,
            "count": r.nr_contracte,
            "nr_contracte": r.nr_contracte,
            "total_ron": float(r.total_ron) if r.total_ron else 0,
        }
        for r in result.all()
    ]}
