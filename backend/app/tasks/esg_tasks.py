"""
ESG scoring Celery tasks.
"""
from __future__ import annotations

import asyncio

from app.tasks.celery_app import celery_app
from app.core.database import get_db_context
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.esg_tasks.recalculate_esg_score_task")
def recalculate_esg_score_task(company_id: int):
    """Recalculate ESG score for a single company."""

    async def _run():
        from app.services.esg_scoring import ESGScoringEngine

        async with get_db_context() as db:
            engine = ESGScoringEngine(db)
            esg = await engine.calculate(company_id)
            await db.commit()

            return {
                "company_id": company_id,
                "score": float(esg.score_total),
                "e": float(esg.score_e),
                "s": float(esg.score_s),
                "g": float(esg.score_g),
            }

    return asyncio.run(_run())


@celery_app.task(name="app.tasks.esg_tasks.batch_recalculate_esg_scores")
def batch_recalculate_esg_scores():
    """Batch recalculate ESG scores for all active companies."""

    async def _run():
        from app.services.esg_scoring import ESGScoringEngine
        from app.models.models import Company
        from sqlalchemy import select

        processed = 0
        failed = 0

        async with get_db_context() as db:
            result = await db.execute(
                select(Company.id).where(Company.stare == "ACTIVA")
            )
            company_ids = [r.id for r in result.all()]

        for cid in company_ids:
            try:
                async with get_db_context() as db:
                    engine = ESGScoringEngine(db)
                    await engine.calculate(cid)
                    await db.commit()
                    processed += 1
            except Exception as e:
                logger.error("esg_batch_failed", company_id=cid, error=str(e))
                failed += 1

        logger.info("esg_batch_complete", processed=processed, failed=failed)
        return {"processed": processed, "failed": failed}

    return asyncio.run(_run())
