"""Import EU/SMIS financing contracts into eu_projects table.

Source: https://data.gov.ro/dataset/informatii-derulare-fonduri-europene-smis
File: Contracte de finantare Septembrie 2016 (latest available CSV)

The SMIS CSV has no CUI field; beneficiary matching is done by normalized
company name against the `companies` table. Only companies that match are
imported (unmatched rows are logged to eu_projects_unmatched.txt).

Usage:
    python scripts/import_eu_projects.py
"""
from __future__ import annotations

import asyncio
import csv
import io
import logging
import os
import re
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db",
)

SMIS_URL = (
    "https://data.gov.ro/dataset/69c6a6a8-e129-4bad-ac25-aa9512907807"
    "/resource/8290ac72-7632-4a10-b811-a228c0f88c41/download/financingcontracts.csv"
)
SURSA_URL = "https://data.gov.ro/dataset/informatii-derulare-fonduri-europene-smis"
UNMATCHED_LOG = _backend / "logs" / "eu_projects_unmatched.txt"

# Column names (from CSV header)
COL_PO = "PO"
COL_SMIS = "Cod SMIS"
COL_TITLU = "Titlu proiect"
COL_BENEFICIAR = "Beneficiar"
COL_BUG_TOTAL = "Bug total"
COL_BUG_ELIG = "Bug chelt elig"
COL_BUG_NERAM_UE = "Bug neram UE"
COL_BUG_NERAM_NAT = "Bug neram nat"
COL_STARE = "Stare"
COL_DATA_APROBARE = "Data aprobare proiect"
COL_DATA_START = "Proj Start Date"
COL_DATA_END = "Proj End Date"


def _normalize_name(name: str) -> str:
    """Normalize company name for fuzzy matching."""
    name = name.upper().strip()
    # Remove legal form suffixes
    name = re.sub(
        r"\b(S\.?A\.?|S\.?R\.?L\.?|S\.?N\.?C\.?|R\.?A\.?|S\.?C\.?|"
        r"S\.?E\.?|P\.?F\.?A\.?|I\.?I\.?|I\.?F\.?)\b\.?",
        "",
        name,
    )
    # Remove punctuation except spaces
    name = re.sub(r"[^\w\s]", " ", name)
    # Collapse spaces
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _parse_amount(val: str) -> int | None:
    """Parse amount string like '12,748,451.15' to integer RON (rounded)."""
    if not val or val.strip() in ("-", ""):
        return None
    cleaned = val.strip().replace(",", "").replace(" ", "")
    try:
        return int(float(cleaned))
    except (ValueError, AttributeError):
        return None


def _parse_date(val: str) -> date | None:
    """Parse DD.MM.YYYY date string."""
    if not val or val.strip() in ("-", ""):
        return None
    val = val.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


async def lookup_company_by_name(conn: asyncpg.Connection, name: str) -> int | None:
    """Look up company_id by normalized name via DB query."""
    # Try exact normalized match using DB-side upper() comparison
    row = await conn.fetchrow(
        "SELECT id FROM companies WHERE upper(regexp_replace(denumire, '[^a-zA-Z0-9 ]', ' ', 'g')) = $1 LIMIT 1",
        _normalize_name(name),
    )
    if row:
        return row["id"]
    return None


async def main() -> None:
    dsn = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )

    log.info("Downloading SMIS contracts CSV...")
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(120.0),
        follow_redirects=True,
        headers={"User-Agent": "RomBiz-ETL/1.0"},
    ) as client:
        resp = await client.get(SMIS_URL)
        resp.raise_for_status()
        content = resp.text

    rows = list(csv.DictReader(io.StringIO(content)))
    log.info("Downloaded %d contract rows", len(rows))

    conn = await asyncpg.connect(dsn, timeout=30)
    try:
        # Create a temporary lookup index in the DB using a temp table
        log.info("Building temp name lookup index in DB...")
        await conn.execute("""
            CREATE TEMP TABLE IF NOT EXISTS _eu_name_lookup AS
            SELECT id, upper(regexp_replace(denumire, '[^a-zA-Z0-9 ]', ' ', 'g')) AS norm_name
            FROM companies
            WHERE denumire IS NOT NULL
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS _eu_name_idx ON _eu_name_lookup(norm_name)")
        log.info("Temp name index built.")

        inserted = 0
        skipped = 0
        unmatched_names: list[str] = []

        for i, row in enumerate(rows):
            if i > 0 and i % 1000 == 0:
                log.info("Progress: %d/%d rows, inserted=%d skipped=%d", i, len(rows), inserted, skipped)

            beneficiar = row.get(COL_BENEFICIAR, "").strip()
            if not beneficiar:
                continue

            norm = _normalize_name(beneficiar)
            company_row = await conn.fetchrow(
                "SELECT id FROM _eu_name_lookup WHERE norm_name = $1 LIMIT 1", norm
            )
            company_id = company_row["id"] if company_row else None

            if not company_id:
                # Try shorter match (first 4 words)
                words = norm.split()
                if len(words) >= 4:
                    short_key = " ".join(words[:4])
                    company_row = await conn.fetchrow(
                        "SELECT id FROM _eu_name_lookup WHERE norm_name = $1 LIMIT 1", short_key
                    )
                    company_id = company_row["id"] if company_row else None

            if not company_id:
                unmatched_names.append(beneficiar)
                skipped += 1
                continue

            po = row.get(COL_PO, "").strip()[:50]
            titlu = row.get(COL_TITLU, "").strip() or None
            valoare = _parse_amount(row.get(COL_BUG_TOTAL, ""))
            finantare_ue = _parse_amount(row.get(COL_BUG_NERAM_UE, ""))
            cofinantare = _parse_amount(row.get(COL_BUG_NERAM_NAT, ""))
            data_aprobare = _parse_date(row.get(COL_DATA_APROBARE, ""))
            data_finalizare = _parse_date(row.get(COL_DATA_END, ""))
            stare = row.get(COL_STARE, "").strip()[:20] or None

            # Compute EU % if possible, clamp to [0, 999.99]
            finantare_pct = None
            if valoare and finantare_ue and valoare > 0:
                pct = round(finantare_ue / valoare * 100, 2)
                finantare_pct = min(pct, 999.99)  # numeric(5,2) max is 999.99

            await conn.execute(
                """
                INSERT INTO eu_projects (
                    company_id, titlu, program_operational,
                    valoare_totala_ron, finantare_ue_ron, finantare_ue_pct,
                    cofinantare_ron, data_aprobare, data_finalizare,
                    status, sursa_url
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                ON CONFLICT DO NOTHING
                """,
                company_id, titlu, po,
                valoare, finantare_ue, finantare_pct,
                cofinantare, data_aprobare, data_finalizare,
                stare, SURSA_URL,
            )
            inserted += 1

        log.info("Done. Inserted: %d, Unmatched: %d", inserted, skipped)
        count = await conn.fetchval("SELECT COUNT(*) FROM eu_projects")
        log.info("eu_projects total rows now: %d", count)

        # Write unmatched names for review
        if unmatched_names:
            UNMATCHED_LOG.parent.mkdir(exist_ok=True)
            with open(UNMATCHED_LOG, "w") as f:
                f.write("\n".join(sorted(set(unmatched_names))))
            log.info("Unmatched beneficiaries written to %s", UNMATCHED_LOG)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
