"""
RedBill (Cambie Roșie) service — debt tracking and aggregation.
"""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Company, CompanyDebt, RedBillCase
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedBillService:
    """Manage debtor profiles and Red Bill reports."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate_company(self, company_id: int) -> dict:
        """
        Evaluate a company's debt profile.
        Aggregates data from ANAF and AEGRM.
        """
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        if not company:
            raise ValueError(f"Company {company_id} not found")

        # Get all debts
        debts_result = await self.db.execute(
            select(CompanyDebt)
            .where(CompanyDebt.company_id == company_id)
            .order_by(CompanyDebt.data_raportare.desc())
        )
        debts = debts_result.scalars().all()

        total_outstanding = sum(
            float(d.suma_restanta or 0) for d in debts
        )

        # Categorize debts
        fiscal_debts = [d for d in debts if d.sursa == "ANAF"]
        other_debts = [d for d in debts if d.sursa != "ANAF"]

        # Check freshness (hard constraint: max 90 days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        fresh_debts = [d for d in debts if d.data_raportare and d.data_raportare >= cutoff.date()]
        stale_debts = [d for d in debts if d.data_raportare and d.data_raportare < cutoff.date()]

        # Risk classification
        risk_level = "green"
        if total_outstanding > 500_000:
            risk_level = "red"
        elif total_outstanding > 100_000:
            risk_level = "orange"
        elif total_outstanding > 10_000:
            risk_level = "yellow"

        return {
            "company_id": company_id,
            "cui": company.cui,
            "denumire": company.denumire,
            "total_outstanding_ron": total_outstanding,
            "risk_level": risk_level,
            "fiscal_debts_count": len(fiscal_debts),
            "other_debts_count": len(other_debts),
            "fresh_data_count": len(fresh_debts),
            "stale_data_count": len(stale_debts),
            "has_debts": company.has_debts,
        }

    async def create_redbill_case(
        self,
        creditor_cui: int,
        debtor_cui: int,
        invoice_number: str,
        invoice_amount: Decimal,
        invoice_date,
        due_date,
        org_id,
        visibility: str = "PUBLIC",
    ) -> RedBillCase:
        """Create a new RedBill case."""
        case = RedBillCase(
            creditor_cui=creditor_cui,
            debtor_cui=debtor_cui,
            invoice_number=invoice_number,
            invoice_amount=invoice_amount,
            invoice_date=invoice_date,
            due_date=due_date,
            org_id=org_id,
            visibility=visibility,
            status="OPEN",
        )
        self.db.add(case)
        await self.db.flush()

        logger.info(
            "redbill_case_created",
            creditor_cui=creditor_cui,
            debtor_cui=debtor_cui,
        )

        return case
