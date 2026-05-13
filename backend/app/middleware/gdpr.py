"""
GDPR compliance middleware and utilities.
Constraint #13: GDPR soft delete cu cascade.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.models import (
    AuditLog, Company, CompanyPerson, FinancialData,
    RiskScore, ESGScore, FraudAlert, Alert,
)

logger = get_logger(__name__)


async def gdpr_soft_delete_company(
    db: AsyncSession,
    company_id: int,
    user_id: UUID,
    reason: str,
) -> dict:
    """
    Soft-delete a company and cascade to all related records.
    Sets deleted_at timestamp instead of hard delete.
    """
    now = datetime.now(timezone.utc)

    # Cascade soft-delete to related tables
    related_models = [
        CompanyPerson,
        FinancialData,
        RiskScore,
        ESGScore,
        FraudAlert,
    ]

    deleted_counts = {}

    for model in related_models:
        if hasattr(model, "deleted_at"):
            result = await db.execute(
                update(model)
                .where(model.company_id == company_id)
                .where(model.deleted_at.is_(None))
                .values(deleted_at=now)
            )
            deleted_counts[model.__tablename__] = result.rowcount

    # Soft-delete the company itself
    await db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(deleted_at=now)
    )

    # Audit log
    audit = AuditLog(
        user_id=user_id,
        actiune="GDPR_DELETE",
        detalii={
            "company_id": company_id,
            "reason": reason,
            "cascade_counts": deleted_counts,
        },
        ip_address="system",
    )
    db.add(audit)
    await db.commit()

    logger.info(
        "gdpr_soft_delete",
        company_id=company_id,
        user_id=str(user_id),
    )

    return {"deleted": True, "cascade": deleted_counts}


async def gdpr_export_user_data(
    db: AsyncSession,
    user_id: UUID,
) -> dict:
    """
    Export all data associated with a user (GDPR Right to Data Portability).
    """
    from app.models.models import User, MonitoredPortfolio, SavedSearch
    from sqlalchemy import select

    # Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"error": "User not found"}

    user_data = {
        "profile": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }

    # Portfolios
    result = await db.execute(
        select(MonitoredPortfolio).where(MonitoredPortfolio.user_id == user_id)
    )
    portfolios = result.scalars().all()
    user_data["portfolios"] = [
        {"name": p.nume, "created_at": p.created_at.isoformat() if p.created_at else None}
        for p in portfolios
    ]

    # Saved searches
    result = await db.execute(
        select(SavedSearch).where(SavedSearch.user_id == user_id)
    )
    searches = result.scalars().all()
    user_data["saved_searches"] = [
        {"name": s.name, "filters": s.filters}
        for s in searches
    ]

    # Alerts
    result = await db.execute(
        select(Alert).where(Alert.user_id == user_id)
    )
    alerts = result.scalars().all()
    user_data["alerts"] = [
        {"type": a.tip_alerta, "message": a.mesaj, "read": a.citita}
        for a in alerts
    ]

    # Audit log
    audit = AuditLog(
        user_id=user_id,
        actiune="GDPR_EXPORT",
        detalii={"status": "completed"},
        ip_address="system",
    )
    db.add(audit)
    await db.commit()

    return user_data


async def gdpr_anonymize_user(
    db: AsyncSession,
    user_id: UUID,
    reason: str,
) -> dict:
    """
    Anonymize user data (GDPR Right to Erasure).
    Replaces PII with anonymized values.
    """
    from app.models.models import User
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"error": "User not found"}

    user.email = f"deleted_{user_id}@anonymized.local"
    user.first_name = "ANONYMIZED"
    user.last_name = "ANONYMIZED"
    user.password_hash = "DELETED"
    user.is_active = False

    # Audit log
    audit = AuditLog(
        user_id=user_id,
        actiune="GDPR_ANONYMIZE",
        detalii={"reason": reason},
        ip_address="system",
    )
    db.add(audit)
    await db.commit()

    logger.info("gdpr_user_anonymized", user_id=str(user_id))

    return {"anonymized": True}
