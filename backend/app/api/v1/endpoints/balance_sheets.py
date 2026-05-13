"""FastAPI endpoint: GET /companies/{cui}/balance-sheets

Returns the full list of annual balance sheets for a given CUI,
sorted descending by an_fiscal.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import CompanyBalanceSheet

router = APIRouter()


# ── Response schema ──────────────────────────────────────────────────────────

class BalanceSheetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cui: int
    an_fiscal: int

    # P&L
    cifra_afaceri: Optional[int] = None
    venituri_totale: Optional[int] = None
    cheltuieli_totale: Optional[int] = None
    profit_brut: Optional[int] = None
    pierdere_bruta: Optional[int] = None
    profit_net: Optional[int] = None
    pierdere_neta: Optional[int] = None

    # Balance sheet
    total_active: Optional[int] = None
    active_imobilizate: Optional[int] = None
    active_circulante: Optional[int] = None
    capitaluri_proprii: Optional[int] = None
    datorii_totale: Optional[int] = None
    datorii_termen_lung: Optional[int] = None

    # Headcount
    nr_salariati: Optional[int] = None

    sursa: str


class BalanceSheetListOut(BaseModel):
    cui: int
    total: int
    items: list[BalanceSheetOut]


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.get(
    "/{cui}/balance-sheets",
    response_model=BalanceSheetListOut,
    summary="Bilanţuri anuale pentru un CUI",
    description=(
        "Returnează lista bilanţurilor anuale importate din fişierele bulk MF/ANAF "
        "pentru CUI-ul dat, sortată descrescător după an_fiscal."
    ),
    tags=["Balance Sheets"],
)
async def get_company_balance_sheets(
    cui: int,
    from_year: Optional[int] = Query(None, ge=2000, le=2100, description="An fiscal minim"),
    to_year: Optional[int] = Query(None, ge=2000, le=2100, description="An fiscal maxim"),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> BalanceSheetListOut:
    stmt = (
        select(CompanyBalanceSheet)
        .where(CompanyBalanceSheet.cui == cui)
        .order_by(CompanyBalanceSheet.an_fiscal.desc())
    )
    if from_year is not None:
        stmt = stmt.where(CompanyBalanceSheet.an_fiscal >= from_year)
    if to_year is not None:
        stmt = stmt.where(CompanyBalanceSheet.an_fiscal <= to_year)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Nu există bilanţuri pentru CUI {cui}.",
        )

    return BalanceSheetListOut(
        cui=cui,
        total=len(rows),
        items=[BalanceSheetOut.model_validate(r) for r in rows],
    )


# ── Admin trigger endpoint ────────────────────────────────────────────────────

class ImportTriggerOut(BaseModel):
    task_id: str
    year: int
    message: str


@router.post(
    "/balance-sheets/import/{year}",
    response_model=ImportTriggerOut,
    summary="Declanşează importul bilanţurilor pentru un an fiscal (admin)",
    tags=["Balance Sheets"],
)
async def trigger_balance_sheet_import(
    year: int,
    _user: TokenPayload = Depends(get_current_user),
) -> ImportTriggerOut:
    """Enqueue a Celery task to import balance sheets for the given year.
    Requires admin role.
    """
    if _user.role != "admin":
        raise HTTPException(status_code=403, detail="Acces restricţionat la admini.")

    from app.tasks.balance_sheets_task import import_balance_sheets_year
    task = import_balance_sheets_year.delay(year)

    return ImportTriggerOut(
        task_id=task.id,
        year=year,
        message=f"Import bilanţuri {year} a fost pus în coadă (task_id={task.id}).",
    )
