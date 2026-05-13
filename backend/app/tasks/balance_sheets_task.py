"""Celery task: annual import of MF/ANAF balance sheets.

Scheduled via Celery Beat to run every January 15 at 02:00 UTC,
which gives the Ministry of Finance time to publish the previous
fiscal year's data (typically released in December–January).

Manual trigger:
    from app.tasks.balance_sheets_task import import_balance_sheets_year
    import_balance_sheets_year.delay(2023)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


def _run_async(coro):
    """Run an async coroutine from within a synchronous Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.tasks.balance_sheets_task.import_balance_sheets_year",
    bind=True,
    max_retries=2,
    default_retry_delay=300,  # 5 min between retries
    time_limit=14400,          # 4 h hard limit per year
    soft_time_limit=13200,     # 3.5 h soft limit
)
def import_balance_sheets_year(self, year: int) -> dict:
    """Download, parse, and upsert balance sheets for a single fiscal *year*.

    Returns a summary dict with insert/error counts.
    """
    logger.info("[balance_sheets] Starting import for year=%d (task_id=%s)", year, self.request.id)

    try:
        from app.etl.balance_sheets.pipeline import run_year
        result = _run_async(run_year(year))
    except Exception as exc:  # noqa: BLE001
        logger.error("[balance_sheets] year=%d failed: %s", year, exc, exc_info=True)
        raise self.retry(exc=exc)

    summary = {
        "year": result.year,
        "success": result.success,
        "inserted": result.inserted,
        "errors": result.errors,
        "zip_path": str(result.zip_path) if result.zip_path else None,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    if not result.success:
        logger.error("[balance_sheets] year=%d result: %s", year, result)
    else:
        logger.info("[balance_sheets] year=%d result: %s", year, result)

    return summary


@celery_app.task(
    name="app.tasks.balance_sheets_task.import_balance_sheets_previous_year",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def import_balance_sheets_previous_year(self) -> dict:
    """Import balance sheets for the previous calendar year.

    Designed to be called by the annual Celery Beat schedule.
    """
    prev_year = datetime.now(timezone.utc).year - 1
    logger.info(
        "[balance_sheets] Annual scheduled run for year=%d (task_id=%s)",
        prev_year,
        self.request.id,
    )
    return import_balance_sheets_year(prev_year)
