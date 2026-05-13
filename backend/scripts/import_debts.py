"""Import ANAF 'Datorii la bugetul de stat' CSVs into company_debts table.

Source: https://data.gov.ro/dataset/datoriile-catre-bugetul-de-stat
Data as of: 31.03.2016 (last published update on data.gov.ro)

One row is inserted per company per debt category (BUGET_DE_STAT,
ASIGURARI_SOCIALE, ASIGURARI_SOMAJ, SANATATE) plus one TOTAL row.
Only non-zero values are inserted.

Usage:
    python scripts/import_debts.py
"""
from __future__ import annotations

import asyncio
import csv
import io
import logging
import sys
from datetime import date
from pathlib import Path

import asyncpg
import httpx

# ── Bootstrap ────────────────────────────────────────────────────────────────
_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
try:
    from dotenv import load_dotenv
    load_dotenv(_backend / ".env", override=False)
except ImportError:
    pass

import os
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db",
)
DATA_RAPORTARE = date(2016, 3, 31)
SURSA = "ANAF_DATORII_2016"

SOURCES = {
    "MARI": "https://data.gov.ro/dataset/238727a2-ffd4-4aa9-9655-814a86721c97/resource/125297c1-78df-4c82-a437-0f6f52aeda86/download/mari.csv",
    "MIJLOCII": "https://data.gov.ro/dataset/238727a2-ffd4-4aa9-9655-814a86721c97/resource/bb24c535-83d8-469b-bf5c-b345d8619ad0/download/mijlocii.csv",
    "MICI": "https://data.gov.ro/dataset/238727a2-ffd4-4aa9-9655-814a86721c97/resource/1a23968b-de59-4e42-88e0-d78155c6706a/download/micijuridice.csv",
}

# Column groups in the CSV (0-indexed after CUI and denumire)
# Positions: [principale, accesorii, contestate] for each category
CATEGORIES = [
    ("BUGET_DE_STAT",       [2, 3, 4]),
    ("ASIGURARI_SOCIALE",   [5, 6, 7]),
    ("ASIGURARI_SOMAJ",     [8, 9, 10]),
    ("SANATATE",            [11, 12, 13]),
]


def _parse_amount(val: str) -> float:
    """Parse amount string, return 0 on invalid."""
    try:
        return float(val.strip().replace(",", ".").replace(" ", "") or 0)
    except (ValueError, AttributeError):
        return 0.0


async def _fetch_csv(url: str) -> list[list[str]]:
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(120.0),
        follow_redirects=True,
        headers={"User-Agent": "RomBiz-ETL/1.0"},
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    content = resp.text
    reader = csv.reader(io.StringIO(content), delimiter="\t")
    return list(reader)


async def import_source(conn: asyncpg.Connection, category_label: str, url: str) -> int:
    log.info("Downloading %s from %s", category_label, url)
    rows = await _fetch_csv(url)
    if not rows:
        log.warning("Empty file for %s", category_label)
        return 0

    # Skip header row
    data_rows = rows[1:]
    log.info("%s: %d data rows", category_label, len(data_rows))

    inserted = 0
    for row in data_rows:
        if len(row) < 14:
            continue

        cui_raw = row[0].strip().strip('"')
        if not cui_raw or not cui_raw.isdigit():
            continue
        cui = int(cui_raw)

        # Look up company_id
        company_id = await conn.fetchval(
            "SELECT id FROM companies WHERE cui = $1", cui
        )
        if not company_id:
            continue

        # Insert one row per non-zero category
        for tip, col_indices in CATEGORIES:
            total = sum(_parse_amount(row[i]) for i in col_indices if i < len(row))
            if total <= 0:
                continue

            await conn.execute(
                """
                INSERT INTO company_debts (company_id, suma_restanta, tip_datorie, data_raportare, sursa)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
                """,
                company_id, total, tip, DATA_RAPORTARE, SURSA,
            )
            inserted += 1

        # Also insert TOTAL row
        total_all = sum(
            _parse_amount(row[i])
            for _, cols in CATEGORIES
            for i in cols
            if i < len(row)
        )
        if total_all > 0:
            await conn.execute(
                """
                INSERT INTO company_debts (company_id, suma_restanta, tip_datorie, data_raportare, sursa)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
                """,
                company_id, total_all, "TOTAL", DATA_RAPORTARE, SURSA,
            )
            inserted += 1

    return inserted


async def main() -> None:
    dsn = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    conn = await asyncpg.connect(dsn, timeout=30)
    try:
        total = 0
        for label, url in SOURCES.items():
            n = await import_source(conn, label, url)
            log.info("%s: inserted %d debt rows", label, n)
            total += n
        log.info("Done. Total rows inserted: %d", total)
        count = await conn.fetchval("SELECT COUNT(*) FROM company_debts")
        log.info("company_debts total rows now: %d", count)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
