"""
Geospatial BI endpoints — Branch 20.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.geospatial_bi import (
    company_heatmap,
    economic_zones,
    proximity_analysis,
    geodemographic_analysis,
    county_analytics,
)

router = APIRouter()


@router.get("/heatmap")
async def get_heatmap(
    caen_code: Optional[str] = None,
    judet: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """20.1 — Company heatmap."""
    return await company_heatmap(db, caen_code, judet)


@router.get("/zones")
async def get_zones(
    caen_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """20.2 — Economic zones."""
    return await economic_zones(db, caen_code)


@router.get("/proximity")
async def get_proximity(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(10, ge=1, le=200),
    caen_code: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """20.3 — Proximity analysis."""
    return await proximity_analysis(db, lat, lng, radius_km, caen_code, limit)


@router.get("/geodemographic/{judet}")
async def get_geodemographic(
    judet: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """20.4 — Geodemographic analysis."""
    return await geodemographic_analysis(db, judet)


@router.get("/counties")
async def get_counties(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """20.5 — County analytics."""
    return await county_analytics(db)
