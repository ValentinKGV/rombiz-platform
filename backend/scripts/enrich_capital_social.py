"""Populate companies.capital_social from balance sheet raw files.

The WEB_BL_BS_SL positional files include col 12 = capital_subscris (= capital social).
This was previously marked 'ignored' in constants.py but is exactly what we need.

We scan cached balance sheet files from most recent year back to 2009, taking
the most-recent non-null value per CUI.

Usage:
    python scripts/enrich_capital_social.py
"""
from __future__ import annotations

import asyncio
import csv
import logging
import os
import sys
from pathlib import Path

import asyncpg

# ── Bootstrap ────────────────────────────────────────────────────────────────
_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
try:
    from dotenv import load_dotenv
    load_dotenv(_backend / ".env", override=False)
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db",
)
CACHE_DIR = Path("/data/bilant_cache")

# Most recent years first
YEARS = list(range(2024, 2008, -1))

# col 0 = CUI, col 12 = capital_subscris (capital social)
COL_CUI = 0
COL_CAPITAL = 12


def _parse_int(val: str) -> int | None:
    v = val.strip()
    if not v:
        return None
    try:
        return int(float(v))
    except (ValueError, AttributeError):
        return None


def build_capital_map() -> dict[int, int]:
    """Build cui→capital_social mapping from cached files (newest year wins)."""
    capital_map: dict[int, int] = {}

    for year in YEARS:
        cache_file = CACHE_DIR / f"bilant{year}.txt"
        if not cache_file.exists():
            log.info("Cache file not found: %s — skipping", cache_file.name)
            continue

        log.info("Reading %s...", cache_file.name)
        count = 0
        new_entries = 0
        with open(cache_file, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            for row in reader:
                count += 1
                if len(row) <= COL_CAPITAL:
                    continue
                cui_val = row[COL_CUI].strip()
                if not cui_val or not cui_val.lstrip("-").isdigit():
                    continue
                try:
                    cui = int(cui_val)
                except ValueError:
                    continue
                if cui <= 0:
                    continue

                # Only set if not already set from a newer year
                if cui in capital_map:
                    continue

                capital_val = _parse_int(row[COL_CAPITAL])
                if capital_val is not None and capital_val > 0:
                    capital_map[cui] = capital_val
                    new_entries += 1

        log.info("%s: %d rows, %d new capital entries (total so far: %d)",
                 cache_file.name, count, new_entries, len(capital_map))

    return capital_map


async def main() -> None:
    capital_map = build_capital_map()
    log.info("Total CUIs with capital_social data: %d", len(capital_map))

    if not capital_map:
        log.warning("No capital data found. Check cache directory.")
        return

    dsn = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    conn = await asyncpg.connect(dsn, timeout=30)
    try:
        # Check current state
        before = await conn.fetchval(
            "SELECT COUNT(*) FROM companies WHERE capital_social IS NOT NULL AND capital_social > 0"
        )
        log.info("companies with capital_social before: %d", before)

        # Bulk update in batches
        cuis = list(capital_map.items())
        batch_size = 5000
        updated = 0

        for i in range(0, len(cuis), batch_size):
            batch = cuis[i : i + batch_size]
            # Use unnest for batch update
            cui_list = [c for c, _ in batch]
            cap_list = [v for _, v in batch]
            result = await conn.execute(
                """
                UPDATE companies
                SET capital_social = u.cap
                FROM (
                    SELECT unnest($1::int[]) AS cui,
                           unnest($2::numeric[]) AS cap
                ) AS u
                WHERE companies.cui = u.cui
                  AND (companies.capital_social IS NULL OR companies.capital_social = 0)
                """,
                cui_list, cap_list,
            )
            n = int(result.split()[-1]) if result else 0
            updated += n
            if i % 50000 == 0:
                log.info("Progress: %d/%d batches, %d updated so far", i, len(cuis), updated)

        after = await conn.fetchval(
            "SELECT COUNT(*) FROM companies WHERE capital_social IS NOT NULL AND capital_social > 0"
        )
        log.info("Done. Updated: %d rows. capital_social coverage: before=%d, after=%d",
                 updated, before, after)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
