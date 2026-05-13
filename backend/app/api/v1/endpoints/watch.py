"""
Watch endpoints — personal company watchlist for the current user.
Uses MonitoredPortfolio with name="__watch__" as the backing store.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import MonitoredPortfolio, PortfolioCompany, Company

router = APIRouter()
_WATCH_NAME = "__watch__"


async def _get_or_create_watch(
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    db: AsyncSession,
) -> MonitoredPortfolio:
    result = await db.execute(
        select(MonitoredPortfolio).where(
            and_(
                MonitoredPortfolio.user_id == user_id,
                MonitoredPortfolio.name == _WATCH_NAME,
            )
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        portfolio = MonitoredPortfolio(
            user_id=user_id,
            org_id=org_id,
            name=_WATCH_NAME,
            description="Personal watchlist",
        )
        db.add(portfolio)
        await db.flush()
    return portfolio


@router.get("")
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Return all companies in the current user's watchlist."""
    user_uuid = uuid.UUID(user.sub)

    result = await db.execute(
        select(MonitoredPortfolio).where(
            and_(
                MonitoredPortfolio.user_id == user_uuid,
                MonitoredPortfolio.name == _WATCH_NAME,
            )
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"companies": [], "count": 0}

    rows_result = await db.execute(
        select(PortfolioCompany, Company)
        .join(Company, PortfolioCompany.company_id == Company.id)
        .where(PortfolioCompany.portfolio_id == portfolio.id)
        .order_by(PortfolioCompany.added_at.desc())
    )
    rows = rows_result.all()
    return {
        "companies": [
            {
                "id": c.id,
                "cui": c.cui,
                "denumire": c.denumire,
                "judet": c.judet,
                "localitate": c.localitate,
                "stare": c.stare,
                "caen_principal": c.caen_principal,
                "has_debts": c.has_debts,
                "has_insolvency": c.has_insolvency,
                "added_at": pc.added_at.isoformat() if pc.added_at else None,
            }
            for pc, c in rows
        ],
        "count": len(rows),
    }


@router.post("/{cui}", status_code=201)
async def add_to_watchlist(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Add a company to the current user's watchlist by CUI."""
    company_result = await db.execute(select(Company).where(Company.cui == cui))
    company = company_result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    user_uuid = uuid.UUID(user.sub)
    org_uuid = uuid.UUID(user.org_id)
    portfolio = await _get_or_create_watch(user_uuid, org_uuid, db)

    existing = await db.execute(
        select(PortfolioCompany).where(
            and_(
                PortfolioCompany.portfolio_id == portfolio.id,
                PortfolioCompany.company_id == company.id,
            )
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Already watching", "cui": cui}

    db.add(PortfolioCompany(portfolio_id=portfolio.id, company_id=company.id))
    await db.commit()
    return {"message": "Added to watchlist", "cui": cui, "denumire": company.denumire}


@router.delete("/{cui}", status_code=200)
async def remove_from_watchlist(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Remove a company from the current user's watchlist by CUI."""
    user_uuid = uuid.UUID(user.sub)

    result = await db.execute(
        select(MonitoredPortfolio).where(
            and_(
                MonitoredPortfolio.user_id == user_uuid,
                MonitoredPortfolio.name == _WATCH_NAME,
            )
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"message": "Not in watchlist"}

    company_result = await db.execute(select(Company).where(Company.cui == cui))
    company = company_result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    await db.execute(
        delete(PortfolioCompany).where(
            and_(
                PortfolioCompany.portfolio_id == portfolio.id,
                PortfolioCompany.company_id == company.id,
            )
        )
    )
    await db.commit()
    return {"message": "Removed from watchlist", "cui": cui}


@router.get("/check/{cui}")
async def check_watching(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Check whether the current user is watching a specific company."""
    user_uuid = uuid.UUID(user.sub)

    result = await db.execute(
        select(MonitoredPortfolio).where(
            and_(
                MonitoredPortfolio.user_id == user_uuid,
                MonitoredPortfolio.name == _WATCH_NAME,
            )
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"watching": False}

    company_result = await db.execute(select(Company).where(Company.cui == cui))
    company = company_result.scalar_one_or_none()
    if not company:
        return {"watching": False}

    existing = await db.execute(
        select(PortfolioCompany).where(
            and_(
                PortfolioCompany.portfolio_id == portfolio.id,
                PortfolioCompany.company_id == company.id,
            )
        )
    )
    return {"watching": existing.scalar_one_or_none() is not None}
