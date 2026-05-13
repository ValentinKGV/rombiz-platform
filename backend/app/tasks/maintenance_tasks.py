"""
Maintenance Celery tasks — materialized views, stale data cleanup.
"""
from __future__ import annotations

import asyncio

from app.tasks.celery_app import celery_app
from app.core.database import get_db_context
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.maintenance_tasks.refresh_materialized_views")
def refresh_materialized_views():
    """Refresh all materialized views concurrently."""

    async def _run():
        from sqlalchemy import text

        views = [
            "mv_company_summary",
            "mv_sector_stats",
            "mv_top_companies_by_county",
        ]

        async with get_db_context() as db:
            for view in views:
                try:
                    await db.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))
                    logger.info("materialized_view_refreshed", view=view)
                except Exception as e:
                    logger.error("materialized_view_refresh_failed", view=view, error=str(e))

            await db.commit()

        return {"views_refreshed": len(views)}

    return asyncio.run(_run())


@celery_app.task(name="app.tasks.maintenance_tasks.cleanup_stale_data")
def cleanup_stale_data():
    """Clean up stale/expired data."""

    async def _run():
        from sqlalchemy import text, delete
        from datetime import datetime, timezone, timedelta

        async with get_db_context() as db:
            # Clean expired sessions/tokens (older than 30 days)
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)

            # Clean old audit logs (older than 1 year)
            audit_cutoff = datetime.now(timezone.utc) - timedelta(days=365)

            # Clean completed report exports older than 7 days
            from app.models.models import ReportExport
            report_cutoff = datetime.now(timezone.utc) - timedelta(days=7)

            result = await db.execute(
                delete(ReportExport).where(
                    ReportExport.created_at < report_cutoff,
                    ReportExport.status == "completed",
                )
            )

            await db.commit()
            logger.info("stale_data_cleanup_complete")

        return {"status": "completed"}

    return asyncio.run(_run())
