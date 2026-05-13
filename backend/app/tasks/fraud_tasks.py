"""
Fraud detection Celery tasks.
"""
from __future__ import annotations

import asyncio

from app.tasks.celery_app import celery_app
from app.core.database import get_db_context
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.fraud_tasks.run_all_detection")
def run_all_detection():
    """Run all fraud detection algorithms."""

    async def _run():
        from app.services.fraud_graph import FraudGraphEngine

        total_alerts = 0

        async with get_db_context() as db:
            engine = FraudGraphEngine(db)

            # 1. Carousel detection
            try:
                carousel_alerts = await engine.detect_carousels()
                for alert in carousel_alerts:
                    db.add(alert)
                total_alerts += len(carousel_alerts)
                logger.info("fraud_carousel_complete", alerts=len(carousel_alerts))
            except Exception as e:
                logger.error("fraud_carousel_failed", error=str(e))

            # 2. Phoenix detection
            try:
                phoenix_alerts = await engine.detect_phoenix()
                for alert in phoenix_alerts:
                    db.add(alert)
                total_alerts += len(phoenix_alerts)
                logger.info("fraud_phoenix_complete", alerts=len(phoenix_alerts))
            except Exception as e:
                logger.error("fraud_phoenix_failed", error=str(e))

            # 3. Cluster detection
            try:
                cluster_alerts = await engine.detect_clusters()
                for alert in cluster_alerts:
                    db.add(alert)
                total_alerts += len(cluster_alerts)
                logger.info("fraud_cluster_complete", alerts=len(cluster_alerts))
            except Exception as e:
                logger.error("fraud_cluster_failed", error=str(e))

            await db.commit()

        logger.info("fraud_detection_complete", total_alerts=total_alerts)
        return {"total_alerts": total_alerts}

    return asyncio.run(_run())


@celery_app.task(name="app.tasks.fraud_tasks.score_company_anomaly")
def score_company_anomaly(company_id: int):
    """Score anomaly for a single company."""

    async def _run():
        from app.services.fraud_graph import FraudGraphEngine

        async with get_db_context() as db:
            engine = FraudGraphEngine(db)
            alert = await engine.score_anomaly(company_id)
            if alert:
                db.add(alert)
                await db.commit()
                return {"company_id": company_id, "alert": True}
            return {"company_id": company_id, "alert": False}

    return asyncio.run(_run())
