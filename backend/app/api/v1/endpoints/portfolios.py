"""
Portfolio management endpoints — portfolios, watched companies, saved searches.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import (
    MonitoredPortfolio, PortfolioCompany, Company,
    SavedSearch, Alert,
)
from app.schemas.schemas import PortfolioCreate, PortfolioSchema, SavedSearchCreate, SavedSearchSchema

router = APIRouter()


def _to_uuid(val):
    """Convert string to UUID if needed."""
    import uuid as _uuid
    if isinstance(val, _uuid.UUID):
        return val
    return _uuid.UUID(str(val))


@router.get("")
async def list_portfolios(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """List all portfolios for the current user."""
    result = await db.execute(
        select(MonitoredPortfolio)
        .where(MonitoredPortfolio.user_id == user.sub)
        .order_by(MonitoredPortfolio.created_at.desc())
    )
    portfolios = result.scalars().all()

    out = []
    for p in portfolios:
        # Count companies in this portfolio
        count_result = await db.execute(
            select(func.count(PortfolioCompany.id))
            .where(PortfolioCompany.portfolio_id == p.id)
        )
        company_count = count_result.scalar() or 0

        out.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "alert_email": p.alert_email,
            "alert_sms": p.alert_sms,
            "alert_webhook": p.alert_webhook,
            "webhook_url": p.webhook_url,
            "org_id": p.org_id,
            "company_count": company_count,
            "created_at": p.created_at,
        })
    return out


@router.post("", response_model=PortfolioSchema, status_code=201)
async def create_portfolio(
    body: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Create a new monitored portfolio."""
    portfolio = MonitoredPortfolio(
        user_id=user.sub,
        org_id=user.org_id,
        name=body.name,
        description=body.description,
    )
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return PortfolioSchema.model_validate(portfolio)


@router.get("/{portfolio_id}")
async def get_portfolio_detail(
    portfolio_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get portfolio with all watched companies."""
    result = await db.execute(
        select(MonitoredPortfolio).where(
            and_(MonitoredPortfolio.id == portfolio_id, MonitoredPortfolio.user_id == user.sub)
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Get companies in portfolio
    companies_result = await db.execute(
        select(PortfolioCompany, Company)
        .join(Company, PortfolioCompany.company_id == Company.id)
        .where(PortfolioCompany.portfolio_id == portfolio_id)
    )
    rows = companies_result.all()

    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "description": portfolio.description,
        "companies": [
            {
                "company_id": pc.company_id,
                "cui": c.cui,
                "denumire": c.denumire,
                "judet": c.judet,
                "stare": c.stare,
                "added_at": pc.added_at,
                "notes": pc.notes,
            }
            for pc, c in rows
        ],
    }


@router.post("/{portfolio_id}/companies")
async def add_company_to_portfolio(
    portfolio_id: str,
    cui: int = Query(...),
    note: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Add a company to a portfolio by CUI."""
    # Verify ownership
    result = await db.execute(
        select(MonitoredPortfolio).where(
            and_(MonitoredPortfolio.id == portfolio_id, MonitoredPortfolio.user_id == user.sub)
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Find company
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company CUI {cui} not found")

    # Check duplicate
    existing = await db.execute(
        select(PortfolioCompany).where(
            and_(
                PortfolioCompany.portfolio_id == portfolio_id,
                PortfolioCompany.company_id == company.id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Company already in portfolio")

    pc = PortfolioCompany(
        portfolio_id=portfolio_id,
        company_id=company.id,
        notes=note,
    )
    db.add(pc)
    await db.commit()
    return {"status": "added", "company_id": company.id, "cui": cui}


@router.delete("/{portfolio_id}/companies/{company_id}")
async def remove_company_from_portfolio(
    portfolio_id: str,
    company_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Remove a company from a portfolio."""
    result = await db.execute(
        select(MonitoredPortfolio).where(
            and_(MonitoredPortfolio.id == portfolio_id, MonitoredPortfolio.user_id == user.sub)
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Portfolio not found")

    await db.execute(
        delete(PortfolioCompany).where(
            and_(
                PortfolioCompany.portfolio_id == portfolio_id,
                PortfolioCompany.company_id == company_id,
            )
        )
    )
    await db.commit()
    return {"status": "removed"}


@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Delete a portfolio and all its company-links."""
    result = await db.execute(
        select(MonitoredPortfolio).where(
            and_(MonitoredPortfolio.id == portfolio_id, MonitoredPortfolio.user_id == user.sub)
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    await db.execute(
        delete(PortfolioCompany).where(PortfolioCompany.portfolio_id == portfolio_id)
    )
    await db.delete(portfolio)
    await db.commit()
    return {"status": "deleted"}


# ── Saved Searches ──

@router.get("/saved-searches", response_model=list[SavedSearchSchema])
async def list_saved_searches(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """List all saved searches for the current user."""
    result = await db.execute(
        select(SavedSearch)
        .where(SavedSearch.user_id == _to_uuid(user.sub))
        .order_by(SavedSearch.created_at.desc())
    )
    return [SavedSearchSchema.model_validate(s) for s in result.scalars().all()]


@router.post("/saved-searches", response_model=SavedSearchSchema, status_code=201)
async def create_saved_search(
    body: SavedSearchCreate,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Save a search query with all its filters."""
    ss = SavedSearch(
        user_id=_to_uuid(user.sub),
        name=body.name,
        filters_json=body.filters_json,
        notify_new=body.notify_new,
    )
    db.add(ss)
    await db.commit()
    await db.refresh(ss)
    return SavedSearchSchema.model_validate(ss)


@router.delete("/saved-searches/{search_id}")
async def delete_saved_search(
    search_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Delete a saved search."""
    result = await db.execute(
        select(SavedSearch).where(
            and_(SavedSearch.id == search_id, SavedSearch.user_id == _to_uuid(user.sub))
        )
    )
    ss = result.scalar_one_or_none()
    if not ss:
        raise HTTPException(status_code=404, detail="Saved search not found")

    await db.delete(ss)
    await db.commit()
    return {"status": "deleted"}
