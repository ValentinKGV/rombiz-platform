#!/usr/bin/env python3
"""
Import Romanian public contracts from TED (Tenders Electronic Daily) CSV data.

Data source: https://data.europa.eu/data/datasets/ted-csv
Covers: Contract Award Notices 2007-2023

For each year:
1. Downloads ZIP from data.europa.eu
2. Parses CSV, filters ISO_COUNTRY_CODE = "RO"
3. Extracts winner CUI from WIN_NATIONALID (strips "RO " prefix)
4. Inserts into public_contracts table
5. Updates has_seap_contracts = TRUE on companies

Checkpoint: logs/import_ted.checkpoint.txt (stores last completed year)
"""
from __future__ import annotations

import asyncio
import asyncpg
import csv
import gzip
import io
import logging
import os
import re
import sys
import zipfile
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import httpx

DSN = "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db"
LOG_DIR = Path(__file__).parent.parent / "logs"
CHECKPOINT_FILE = LOG_DIR / "import_ted.checkpoint.txt"
TED_CACHE_DIR = LOG_DIR / "ted_cache"
TED_CACHE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

# Annual TED Contract Award Notice URLs (non-deprecated individual years)
TED_URLS = {
    2007: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2007.zip",
    2008: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2008.zip",
    2009: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2009.zip",
    2010: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2010.zip",
    2011: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2011.zip",
    2012: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2012.zip",
    2013: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2013.zip",
    2014: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2014.zip",
    2015: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2015.zip",
    2016: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2016.zip",
    2017: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2017.zip",
    2018: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2018.zip",
    2019: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2019.zip",
    2020: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2020.zip",
    2021: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2021.zip",
    2022: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2022.zip",
    2023: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2023.zip",
}

# Map TED TOP_TYPE to readable procedure
PROC_MAP = {
    "OPE": "licitatie_deschisa", "RES": "licitatie_restransa",
    "COM": "dialog_competitiv", "NEG": "negociere",
    "SOC": "concurs_solutii", "QUA": "calificare",
    "SIN": "sursa_unica", "": "nedefinit",
}


def strip_quotes(s: str) -> str:
    return s.strip().strip('"').strip("'").strip()


def extract_cuis(win_nationalid: str) -> list[int]:
    """Extract integer CUIs from WIN_NATIONALID field.

    Format examples:
      "RO 25198460"        → [25198460]
      "RO 17103310---RO 24357117" → [17103310, 24357117]
      ""                   → []
    """
    val = strip_quotes(win_nationalid)
    if not val:
        return []
    cuis = []
    for part in val.split("---"):
        part = part.strip()
        # Must start with "RO" (Romanian national ID)
        if not part.upper().startswith("RO"):
            continue
        # Extract digits only
        digits = re.sub(r"[^\d]", "", part)
        if not digits:
            continue
        try:
            cui = int(digits)
            if 1 <= cui <= 2_147_483_647:
                cuis.append(cui)
        except ValueError:
            pass
    return cuis


def parse_date(s: str) -> Optional[date]:
    s = strip_quotes(s)
    if not s:
        return None
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def parse_value(s: str) -> Optional[float]:
    s = strip_quotes(s)
    if not s:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def load_checkpoint() -> int:
    """Return last completed year, or 2006 if none."""
    if CHECKPOINT_FILE.exists():
        try:
            return int(CHECKPOINT_FILE.read_text().strip())
        except ValueError:
            pass
    return 2006


def save_checkpoint(year: int) -> None:
    CHECKPOINT_FILE.write_text(str(year))


async def download_year(year: int) -> bytes:
    """Download TED ZIP for given year (with caching)."""
    cache_file = TED_CACHE_DIR / f"ted_can_{year}.zip"
    if cache_file.exists():
        size = cache_file.stat().st_size
        if size > 100_000:  # at least 100KB
            log.info("Year %d: using cached file (%d MB)", year, size // 1_000_000)
            return cache_file.read_bytes()

    # Check if we already have the 2022 file at /tmp/ted_2022.zip (downloaded earlier)
    if year == 2022:
        tmp = Path("/tmp/ted_2022.zip")
        if tmp.exists() and tmp.stat().st_size > 100_000:
            data = tmp.read_bytes()
            cache_file.write_bytes(data)
            log.info("Year 2022: using /tmp/ted_2022.zip (%d MB)", len(data) // 1_000_000)
            return data

    url = TED_URLS[year]
    log.info("Year %d: downloading from %s", year, url)
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.content
                log.info("Year %d: downloaded %d MB", year, len(data) // 1_000_000)
                cache_file.write_bytes(data)
                return data
            except Exception as e:
                if attempt < 2:
                    log.warning("Year %d download attempt %d failed: %s", year, attempt+1, e)
                    await asyncio.sleep(10)
                else:
                    raise


def iter_ro_rows(data: bytes):
    """Yield rows from TED ZIP where contracting country is Romania."""
    z = zipfile.ZipFile(io.BytesIO(data))
    csv_name = z.namelist()[0]
    with z.open(csv_name) as f:
        reader = csv.DictReader(
            io.TextIOWrapper(f, encoding="utf-8", errors="replace")
        )
        for row in reader:
            if strip_quotes(row.get("ISO_COUNTRY_CODE", "")) == "RO":
                yield row


async def process_year(year: int, pool: asyncpg.Pool) -> dict:
    """Process one year of TED data. Returns stats."""
    stats = {"rows": 0, "contracts_inserted": 0, "companies_flagged": 0, "skipped_no_cui": 0}

    data = await download_year(year)

    log.info("Year %d: streaming CSV, collecting RO rows...", year)

    # Parse all RO rows into lightweight tuples (streaming, no full dict in mem)
    # (cui, cae_nationalid, cae_name, nr_contract, title, cpv, tip, valoare, dt_award, url)
    raw_rows: list[tuple] = []
    z = zipfile.ZipFile(io.BytesIO(data))
    csv_name = z.namelist()[0]
    with z.open(csv_name) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"))
        for row in reader:
            stats["rows"] += 1
            if strip_quotes(row.get("ISO_COUNTRY_CODE", "")) != "RO":
                continue
            cuis = extract_cuis(row.get("WIN_NATIONALID", ""))
            if not cuis:
                stats["skipped_no_cui"] += 1
                continue
            cae_nat = strip_quotes(row.get("CAE_NATIONALID", ""))[:20] or None
            cae_name = strip_quotes(row.get("CAE_NAME", ""))[:499] or None
            nr = strip_quotes(row.get("CONTRACT_NUMBER", ""))[:100] or None
            title = strip_quotes(row.get("TITLE", "")) or None
            cpv = strip_quotes(row.get("CPV", ""))[:20] or None
            tip = PROC_MAP.get(strip_quotes(row.get("TOP_TYPE", "")), None)
            valoare = parse_value(row.get("AWARD_VALUE_EURO", ""))
            dt = parse_date(row.get("DT_AWARD", ""))
            ted_url_raw = strip_quotes(row.get("TED_NOTICE_URL", ""))
            url = (f"https://{ted_url_raw}" if ted_url_raw and not ted_url_raw.startswith("http") else ted_url_raw) or None
            for cui in cuis:
                raw_rows.append((cui, cae_nat, cae_name, nr, title, cpv, tip, valoare, dt, url))

    del data  # free zip bytes
    log.info("Year %d: %d RO contract rows (distinct CUIs: %d)", year, len(raw_rows),
             len(set(r[0] for r in raw_rows)))

    if not raw_rows:
        return stats

    # Use temp table + SQL JOIN to resolve company_id without loading full companies table
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TEMP TABLE IF NOT EXISTS _ted_stage (
                cui integer,
                cae_cui text, cae_name text, nr_contract text, title text,
                cpv text, tip text, valoare numeric, dt_award date, url text
            )
        """)
        await conn.execute("TRUNCATE _ted_stage")

        # Insert staged rows in chunks
        CHUNK = 10_000
        for i in range(0, len(raw_rows), CHUNK):
            chunk = raw_rows[i:i+CHUNK]
            await conn.executemany(
                "INSERT INTO _ted_stage VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)",
                chunk
            )

        # INSERT into public_contracts via JOIN
        result = await conn.execute("""
            INSERT INTO public_contracts
              (company_id, autoritate_contractanta_cui, autoritate_contractanta,
               nr_contract, titlu_contract, cod_cpv, tip_procedura,
               valoare, moneda, data_atribuire, seap_url)
            SELECT c.id, s.cae_cui, s.cae_name, s.nr_contract, s.title,
                   s.cpv, s.tip, s.valoare, 'EUR', s.dt_award, s.url
            FROM _ted_stage s
            JOIN companies c ON c.cui = s.cui
        """)
        stats["contracts_inserted"] = int(result.split()[-1])

        # Flag companies
        result2 = await conn.execute("""
            UPDATE companies c
            SET has_seap_contracts = TRUE
            FROM (SELECT DISTINCT s.cui FROM _ted_stage s JOIN companies cc ON cc.cui = s.cui) t
            WHERE c.cui = t.cui AND (c.has_seap_contracts IS NULL OR c.has_seap_contracts = FALSE)
        """)
        stats["companies_flagged"] = int(result2.split()[-1])

        await conn.execute("TRUNCATE _ted_stage")

    log.info(
        "Year %d DONE: rows=%d inserted=%d companies_flagged=%d skipped_no_cui=%d",
        year, stats["rows"], stats["contracts_inserted"], stats["companies_flagged"], stats["skipped_no_cui"]
    )
    return stats


async def main() -> None:
    last_done = load_checkpoint()
    years_to_process = [y for y in sorted(TED_URLS.keys()) if y > last_done]

    if not years_to_process:
        log.info("All years already processed (checkpoint=%d)", last_done)
        return

    log.info("Processing years: %s (last done: %d)", years_to_process, last_done)

    pool = await asyncpg.create_pool(DSN, min_size=2, max_size=4)

    total_inserted = 0
    total_flagged = 0

    for year in years_to_process:
        try:
            stats = await process_year(year, pool)
            total_inserted += stats["contracts_inserted"]
            total_flagged += stats["companies_flagged"]
            save_checkpoint(year)
        except Exception as e:
            log.error("Year %d failed: %s", year, e, exc_info=True)
            log.info("Stopping at year %d (checkpoint saved up to %d)", year, year - 1)
            break

    await pool.close()
    log.info("DONE. Total contracts inserted: %d, companies flagged: %d", total_inserted, total_flagged)

    # Final DB stats
    import asyncpg as _apg
    conn = await _apg.connect(DSN)
    cnt = await conn.fetchval("SELECT COUNT(*) FROM public_contracts")
    flagged = await conn.fetchval("SELECT COUNT(*) FROM companies WHERE has_seap_contracts = TRUE")
    await conn.close()
    log.info("DB final: public_contracts=%d, has_seap_contracts companies=%d", cnt, flagged)


if __name__ == "__main__":
    asyncio.run(main())
