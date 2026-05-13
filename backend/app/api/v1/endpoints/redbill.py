"""
RedBill (Cambie Roșie) endpoints — debtor tracking system.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import Company, RedBillCase, CompanyDebt
from app.schemas.schemas import RedBillReportRequest

router = APIRouter()


@router.get("/{cui}")
async def get_redbill_profile(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Get RedBill (Cambie Roșie) profile for a company.
    Aggregates debt data from ANAF + AEGRM.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get RedBill cases (as debtor)
    cases_result = await db.execute(
        select(RedBillCase)
        .where(RedBillCase.debtor_cui == company.cui)
        .order_by(RedBillCase.created_at.desc())
    )
    cases = cases_result.scalars().all()

    # Get debts
    debts_result = await db.execute(
        select(CompanyDebt)
        .where(CompanyDebt.company_id == company.id)
        .order_by(CompanyDebt.data_raportare.desc())
    )
    debts = debts_result.scalars().all()

    total_debts = sum(float(d.suma_restanta) for d in debts if d.suma_restanta)

    # Compute risk classification based on total debts
    if total_debts <= 0:
        risk_classification = "green"
    elif total_debts < 50_000:
        risk_classification = "yellow"
    elif total_debts < 500_000:
        risk_classification = "orange"
    else:
        risk_classification = "red"

    # Compute freshness in days from most recent debt report
    freshness_days = 0
    if debts:
        from datetime import date as _date
        latest = max((d.data_raportare for d in debts if d.data_raportare), default=None)
        if latest:
            freshness_days = (_date.today() - latest).days

    return {
        "cui": cui,
        "denumire": company.denumire,
        "total_datorii": total_debts,
        "total_datorii_restante": total_debts,
        "risk_classification": risk_classification,
        "freshness_days": freshness_days,
        "datorii": [
            {
                "sursa": d.sursa,
                "tip": d.tip_datorie,
                "tip_datorie": d.tip_datorie,
                "suma": float(d.suma_restanta) if d.suma_restanta else None,
                "suma_restanta": float(d.suma_restanta) if d.suma_restanta else None,
                "data_constatare": str(d.data_raportare) if d.data_raportare else None,
                "data_raportare": d.data_raportare,
            }
            for d in debts
        ],
        "cazuri_cambie": [
            {
                "id": c.id,
                "creditor_cui": c.creditor_cui,
                "invoice_number": c.invoice_number,
                "invoice_amount": float(c.invoice_amount) if c.invoice_amount else None,
                "invoice_date": c.invoice_date,
                "due_date": c.due_date,
                "status": c.status,
                "created_at": c.created_at,
            }
            for c in cases
        ],
    }


@router.post("/report")
async def generate_redbill_report(
    body: RedBillReportRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Generate a RedBill PDF report for a company.
    Dispatches to Celery for async generation.
    """
    result = await db.execute(select(Company).where(Company.cui == body.cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    from app.tasks.report_tasks import generate_redbill_report_task
    task = generate_redbill_report_task.delay(
        company_id=company.id,
        format=body.format or "pdf",
        include_sections=body.include_sections,
    )

    return {
        "status": "generating",
        "task_id": str(task.id),
        "message": "Report will be available for download when ready.",
    }


@router.get("/stats/overview")
async def redbill_stats(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Global RedBill statistics.
    """
    # Total companies with active debts
    total_debtors = await db.execute(
        select(func.count(func.distinct(CompanyDebt.company_id)))
        .where(CompanyDebt.suma_restanta > 0)
    )

    # Total outstanding amount
    total_amount = await db.execute(
        select(func.sum(CompanyDebt.suma_restanta))
        .where(CompanyDebt.suma_restanta > 0)
    )

    # By debt type
    by_type = await db.execute(
        select(
            CompanyDebt.tip_datorie,
            func.count().label("cnt"),
            func.sum(CompanyDebt.suma_restanta).label("total"),
        )
        .where(CompanyDebt.suma_restanta > 0)
        .group_by(CompanyDebt.tip_datorie)
    )

    return {
        "total_debtors": total_debtors.scalar() or 0,
        "total_outstanding_ron": float(total_amount.scalar() or 0),
        "by_type": [
            {
                "tip_datorie": r.tip_datorie,
                "count": r.cnt,
                "total_ron": float(r.total) if r.total else 0,
            }
            for r in by_type.all()
        ],
    }
