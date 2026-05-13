"""ETL pipeline orchestrator: download → parse → upsert.

Public entry point:
    result = await run_year(2023)
    results = await run_years([2021, 2022, 2023])
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.core.database import AsyncSessionLocal

from .downloader import ensure_downloaded
from .parser import iter_rows
from .upsert import upsert_batches

logger = logging.getLogger(__name__)


@dataclass
class YearResult:
    year: int
    zip_path: Path | None = None
    inserted: int = 0
    errors: int = 0
    exc: Exception | None = None

    @property
    def success(self) -> bool:
        return self.exc is None

    def __str__(self) -> str:
        if self.exc:
            return f"year={self.year} FAILED: {self.exc}"
        return (
            f"year={self.year}  inserted/updated={self.inserted}  errors={self.errors}"
        )


async def run_year(year: int) -> YearResult:
    """Full pipeline for a single fiscal year.

    Steps:
      1. Download ZIP (cached if already on disk)
      2. Parse CSV inside ZIP into row dicts
      3. Upsert batches into PostgreSQL

    Returns a YearResult with counts.
    """
    result = YearResult(year=year)
    logger.info("=== Starting balance-sheet ETL for year %d ===", year)

    # ── Step 1: Download ─────────────────────────────────────────────────────
    try:
        zip_path = await ensure_downloaded(year)
        result.zip_path = zip_path
        logger.info("[%d] Download OK: %s", year, zip_path)
    except Exception as exc:  # noqa: BLE001
        logger.error("[%d] Download FAILED: %s", year, exc)
        result.exc = exc
        return result

    # ── Step 2: Parse (synchronously, files are small ~9MB) ─────────────────
    try:
        parsed_rows = list(iter_rows(zip_path, year))
        logger.info("[%d] Parsed %d rows", year, len(parsed_rows))
    except Exception as exc:  # noqa: BLE001
        logger.error("[%d] Parse FAILED: %s", year, exc)
        result.exc = exc
        return result

    # ── Step 3: Upsert ───────────────────────────────────────────────────────
    try:
        async with AsyncSessionLocal() as session:
            async def _row_iter():
                for r in parsed_rows:
                    yield r

            ok, err = await upsert_batches(session, _row_iter())
            result.inserted = ok
            result.errors = err

    except Exception as exc:  # noqa: BLE001
        logger.error("[%d] Upsert FAILED: %s", year, exc, exc_info=True)
        result.exc = exc
        return result

    logger.info(
        "=== Finished year %d: inserted/updated=%d  errors=%d ===",
        year,
        result.inserted,
        result.errors,
    )
    return result


async def run_years(years: list[int]) -> list[YearResult]:
    """Run the pipeline for multiple years sequentially (one year at a time
    to avoid hitting download servers too aggressively).
    """
    results: list[YearResult] = []
    for year in years:
        result = await run_year(year)
        results.append(result)
        if not result.success:
            logger.warning(
                "Year %d failed, continuing with remaining years", year
            )
    return results
