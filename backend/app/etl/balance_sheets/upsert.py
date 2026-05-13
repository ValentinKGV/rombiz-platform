"""Async upsert of parsed balance-sheet rows into PostgreSQL.

Uses raw asyncpg executemany with ON CONFLICT DO UPDATE for maximum
throughput on large batches (millions of rows).
"""
from __future__ import annotations

import logging
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .constants import UPSERT_BATCH_SIZE

logger = logging.getLogger(__name__)

# All writable fields on company_balance_sheets (excluding id / created_at)
_UPSERT_FIELDS: list[str] = [
    "cui",
    "an_fiscal",
    "cifra_afaceri",
    "venituri_totale",
    "cheltuieli_totale",
    "profit_brut",
    "pierdere_bruta",
    "profit_net",
    "pierdere_neta",
    "total_active",
    "active_imobilizate",
    "active_circulante",
    "capitaluri_proprii",
    "datorii_totale",
    "datorii_termen_lung",
    "nr_salariati",
    "sursa",
]

# Build the SQL once at module load
_COLS = ", ".join(_UPSERT_FIELDS)
_PARAMS = ", ".join(f":{f}" for f in _UPSERT_FIELDS)
_UPDATE_SET = ", ".join(
    f"{f} = EXCLUDED.{f}"
    for f in _UPSERT_FIELDS
    if f not in ("cui", "an_fiscal")
)

_UPSERT_SQL = text(f"""
    INSERT INTO company_balance_sheets ({_COLS})
    VALUES ({_PARAMS})
    ON CONFLICT (cui, an_fiscal)
    DO UPDATE SET
        {_UPDATE_SET},
        updated_at = now()
""")


async def upsert_batches(
    session: AsyncSession,
    rows: AsyncIterator[dict],
) -> tuple[int, int]:
    """Consume *rows* async iterator, upsert in batches.

    Returns (inserted_or_updated, errors).
    """
    batch: list[dict] = []
    total_ok = total_err = 0

    async def _flush(b: list[dict]) -> tuple[int, int]:
        ok = err = 0
        # Ensure every row has 'sursa' default
        for r in b:
            r.setdefault("sursa", "MF_BULK")
            # Fill missing optional fields with None so the mapping is complete
            for f in _UPSERT_FIELDS:
                r.setdefault(f, None)
        try:
            await session.execute(_UPSERT_SQL, b)
            await session.commit()
            ok = len(b)
            logger.debug("Upserted batch of %d rows", ok)
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            logger.error("Batch upsert failed (%d rows): %s", len(b), exc, exc_info=True)
            err = len(b)
        return ok, err

    async for row in rows:
        batch.append(row)
        if len(batch) >= UPSERT_BATCH_SIZE:
            ok, err = await _flush(batch)
            total_ok += ok
            total_err += err
            batch = []

    if batch:
        ok, err = await _flush(batch)
        total_ok += ok
        total_err += err

    return total_ok, total_err


def sync_upsert_batches(session: AsyncSession, rows_iter, loop) -> tuple[int, int]:
    """Thin sync wrapper — not used in production; kept for CLI convenience."""
    import asyncio

    async def _run():
        async def _aiter():
            for r in rows_iter:
                yield r
        return await upsert_batches(session, _aiter())

    return loop.run_until_complete(_run())
