"""Synchronous batch upsert using psycopg2 (for ETL CLI usage).

Bypasses asyncpg/SQLAlchemy to avoid SSL connection issues that occur
when running outside the FastAPI event loop context.
"""
from __future__ import annotations

import logging
from typing import Iterator

import psycopg2
import psycopg2.extras

from app.core.config import settings
from .constants import UPSERT_BATCH_SIZE

logger = logging.getLogger(__name__)

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

_COLS = ", ".join(_UPSERT_FIELDS)
_PLACEHOLDERS = ", ".join(f"%({f})s" for f in _UPSERT_FIELDS)
_UPDATE_SET = ", ".join(
    f"{f} = EXCLUDED.{f}"
    for f in _UPSERT_FIELDS
    if f not in ("cui", "an_fiscal")
)

_SQL = f"""
    INSERT INTO company_balance_sheets ({_COLS})
    VALUES ({_PLACEHOLDERS})
    ON CONFLICT (cui, an_fiscal)
    DO UPDATE SET
        {_UPDATE_SET},
        updated_at = now()
"""


def _get_dsn() -> str:
    """Convert the asyncpg DSN to a psycopg2-compatible DSN."""
    url = settings.DATABASE_URL
    # Strip the async driver prefix
    return url.replace("postgresql+asyncpg://", "postgresql://")


def upsert_rows_sync(rows: Iterator[dict]) -> tuple[int, int]:
    """Upsert rows in batches using psycopg2. Returns (inserted, errors)."""
    dsn = _get_dsn()
    total_ok = total_err = 0

    conn = psycopg2.connect(dsn)
    try:
        batch: list[dict] = []

        def _flush(b: list[dict]) -> tuple[int, int]:
            ok = err = 0
            for r in b:
                r.setdefault("sursa", "MF_BULK")
                for f in _UPSERT_FIELDS:
                    r.setdefault(f, None)
            try:
                with conn.cursor() as cur:
                    psycopg2.extras.execute_batch(cur, _SQL, b, page_size=UPSERT_BATCH_SIZE)
                conn.commit()
                ok = len(b)
                logger.debug("Upserted batch of %d rows", ok)
            except Exception as exc:  # noqa: BLE001
                conn.rollback()
                logger.error("Batch upsert failed (%d rows): %s", len(b), exc)
                err = len(b)
            return ok, err

        for row in rows:
            batch.append(row)
            if len(batch) >= UPSERT_BATCH_SIZE:
                ok, err = _flush(batch)
                total_ok += ok
                total_err += err
                batch = []

        if batch:
            ok, err = _flush(batch)
            total_ok += ok
            total_err += err

    finally:
        conn.close()

    return total_ok, total_err
