#!/usr/bin/env python3
"""
Bulk import firme din ONRC open data (data.gov.ro) + enrichment ANAF.

══════════════════════════════════════════════════════════════════════
SURSE DE DATE (open data, descărcare gratuită):

  OD_FIRME.CSV              — ~2.9M firme: denumire, CUI, J-nr,
                              dată înregistrare, formă juridică, adresă
  OD_REPREZENTANTI_LEGALI.CSV — administratori, asociați, cenzori
  ANAF async API            — TVA, CAEN principal, inactiv fiscal
                              (batches de 500 CUI, 1 req/sec)

FAZE:
  Faza 1 (--phase 1):  CSV ONRC → companies table          (~30-60 min)
  Faza 2 (--phase 2):  ANAF enrichment TVA + CAEN           (~2-3 ore)
  Faza 3 (--phase 3):  Reprezentanți legali → company_persons (~20 min)

UTILIZARE:
  cd /home/aether/app/RATING/ATH-Firme/rombiz-platform/backend
  source venv/bin/activate

  # Toate fazele (recomandat):
  python3 scripts/bulk_import_onrc.py

  # Doar o fază specificată:
  python3 scripts/bulk_import_onrc.py --only 1
  python3 scripts/bulk_import_onrc.py --only 2
  python3 scripts/bulk_import_onrc.py --only 3

  # Test cu primele 10.000 firme:
  python3 scripts/bulk_import_onrc.py --limit 10000 --only 1

  # Continuă de unde s-a oprit (după o întrerupere):
  python3 scripts/bulk_import_onrc.py --resume

  # Folosește fișiere CSV deja descărcate local:
  python3 scripts/bulk_import_onrc.py --firme-csv /tmp/od_firme.csv
══════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import httpx
import asyncpg

# ── Bootstrap ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

_env_file = BACKEND_DIR / ".env"
if _env_file.exists():
    # Parse .env manually (no python-dotenv dependency required)
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = BACKEND_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "bulk_import_onrc.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("bulk_import")

# ── URLs — April 2026 dataset (most recent as of script creation) ─────────────
DATASET_BASE = "https://data.gov.ro/dataset/61267ba7-244f-4fc7-9a93-1f54d47586dc/resource"
ONRC_FIRME_URL = f"{DATASET_BASE}/9a7fdaba-0cb7-4355-a2df-3f6506e7829e/download/od_firme.csv"
ONRC_REPREZ_URL = f"{DATASET_BASE}/73619447-d199-4b89-a80f-8c5056e77c8e/download/od_reprezentanti_legali.csv"

ANAF_URL = "https://webservicesp.anaf.ro/AsynchWebService/api/v8/ws/tva"
ANAF_BATCH = 500
ANAF_DELAY = 1.1   # seconds between requests (ANAF rate limit: 1 req/sec)

PROGRESS_FILE = LOG_DIR / "bulk_import_progress.json"

# ── forma_juridica mapping: ONRC codes → DB constraint (SRL/SA/PFA/RA/SNC/SCS/ALT) ──
_FORMA_MAP: dict[str, str] = {
    "SRL": "SRL", "S.R.L": "SRL",
    "SA": "SA",   "S.A.": "SA",
    "SNC": "SNC", "S.N.C": "SNC",
    "SCS": "SCS", "S.C.S": "SCS",
    "RA": "RA",
    "PFA": "PFA", "PF": "PFA",   # Persoana Fizica Autorizata
    # Everything else → ALT
    "AF": "ALT",   # Asociatie Familiala (replaced by IF)
    "II": "ALT",   # Intreprindere Individuala
    "IF": "ALT",   # Intreprindere Familiala
    "ONG": "ALT",
    "RI": "ALT",   # Regie de Interes Local
    "R": "ALT",    # Regie
    "CN": "ALT",   # Companie Nationala
    "CNA": "ALT",  # Companie Nationala
    "SCA": "ALT",  # Societate Civila Avocati
    "SC": "ALT",   # Societate Civila
    "COOP": "ALT", # Cooperativa
}

# ── calitate → tip person mapping (company_persons.tip CHECK constraint) ──────
_CALITATE_MAP: dict[str, str] = {
    "administrator": "ADMINISTRATOR",
    "administrator special": "ADMINISTRATOR",
    "administrator judiciar": "ADMINISTRATOR",
    "asociat": "ASOCIAT",
    "asociat unic": "ASOCIAT",
    "actionar": "ASOCIAT",
    "actionar majoritar": "ASOCIAT",
    "fondator": "ASOCIAT",
    "cenzor": "CENZOR",
    "cenzor supleant": "CENZOR",
    "auditor": "AUDITOR",
    "auditor financiar": "AUDITOR",
    "auditor intern": "AUDITOR",
    "lichidator": "ADMINISTRATOR",
    "lichidator judiciar": "ADMINISTRATOR",
    "director": "ADMINISTRATOR",
    "director general": "ADMINISTRATOR",
    "director executiv": "ADMINISTRATOR",
    "presedinte": "ADMINISTRATOR",
    "vicepresedinte": "ADMINISTRATOR",
    "reprezentant permanent": "ADMINISTRATOR",
    "imputernicit": "ADMINISTRATOR",
    "persoana desemnata": "ADMINISTRATOR",
}


# ── Helper functions ──────────────────────────────────────────────────────────

def _map_forma(onrc_code: str) -> str:
    code = (onrc_code or "").strip().upper()
    return _FORMA_MAP.get(code, "ALT")


def _map_calitate(calitate: str) -> Optional[str]:
    cal = (calitate or "").strip().lower()
    return _CALITATE_MAP.get(cal)


_INT32_MAX = 2_147_483_647  # PostgreSQL INTEGER max (Company.cui column type)


def _parse_cui(s: str) -> Optional[int]:
    try:
        v = int((s or "").strip())
        # CUIs valide: 1 – 2.1B (int32). Valori mai mari = date corupte în CSV.
        return v if 0 < v <= _INT32_MAX else None
    except (ValueError, TypeError):
        return None


def _parse_date_dmy(s: str) -> Optional[date]:
    """Parse date in multiple formats: DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD."""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _clean(s: str, maxlen: int = None) -> Optional[str]:
    v = (s or "").strip()
    if not v:
        return None
    return v[:maxlen] if maxlen else v


def _build_address(row: dict) -> Optional[str]:
    """Compose full address string from ONRC CSV fields."""
    strada = _clean(row.get("ADR_DEN_STRADA", ""))
    nr     = _clean(row.get("ADR_NR_STRADA", ""))
    bloc   = _clean(row.get("ADR_BLOC", ""))
    scara  = _clean(row.get("ADR_SCARA", ""))
    etaj   = _clean(row.get("ADR_ETAJ", ""))
    ap     = _clean(row.get("ADR_APARTAMENT", ""))
    loc    = _clean(row.get("ADR_LOCALITATE", ""))
    jud    = _clean(row.get("ADR_JUDET", ""))
    sector = _clean(row.get("ADR_SECTOR", ""))
    det    = _clean(row.get("ADR_COMPLETARE", ""))

    parts = []
    if strada:
        addr = strada
        if nr:    addr += f" nr.{nr}"
        if bloc:  addr += f", bl.{bloc}"
        if scara: addr += f", sc.{scara}"
        if etaj:  addr += f", et.{etaj}"
        if ap:    addr += f", ap.{ap}"
        parts.append(addr)
    if sector:
        parts.append(f"Sector {sector}")
    if loc:
        parts.append(loc)
    if jud and jud != loc:
        parts.append(f"jud.{jud}")
    if det:
        parts.append(det)

    result = ", ".join(filter(None, parts))
    return result[:1000] if result else None


# ── Database helpers ──────────────────────────────────────────────────────────

def _pg_dsn() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        log.error("DATABASE_URL nu e setat în .env!")
        sys.exit(1)
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def get_pool() -> asyncpg.Pool:
    dsn = _pg_dsn()
    log.info(f"Conectare la DB: {dsn.split('@')[-1]}")
    return await asyncpg.create_pool(dsn, min_size=2, max_size=8, command_timeout=600)


# ── Progress tracking ─────────────────────────────────────────────────────────

def _load_progress() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except Exception:
            pass
    return {"phase1_done": False, "phase1_rows": 0,
            "phase2_done": False, "phase2_last_cui": 0,
            "phase3_done": False, "phase3_rows": 0}


def _save_progress(p: dict):
    PROGRESS_FILE.write_text(json.dumps(p, indent=2))


# ════════════════════════════════════════════════════════════════════════════════
# FAZA 1 — Import OD_FIRME.CSV → companies
# ════════════════════════════════════════════════════════════════════════════════

async def _download_csv(url: str, dest: Path):
    """Download CSV to local file with progress logging."""
    log.info(f"  Descărcând: {url}")
    log.info(f"  Destinație: {dest}")
    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            done = 0
            with open(dest, "wb") as f:
                async for chunk in resp.aiter_bytes(65536):
                    f.write(chunk)
                    done += len(chunk)
                    if total and done % (20 * 1024 * 1024) < 65536:
                        log.info(f"    {done / 1024 / 1024:.0f} MB / {total / 1024 / 1024:.0f} MB")
    log.info(f"  Descărcat complet: {dest.stat().st_size / 1024 / 1024:.1f} MB")


async def phase1_import_firme(
    pool: asyncpg.Pool,
    csv_url: str,
    csv_local: Optional[str],
    limit: int,
    resume_from: int,
) -> int:
    """
    Stream OD_FIRME.CSV and bulk-insert companies.
    Uses INSERT … ON CONFLICT (cui) DO NOTHING for idempotency.
    Returns approximate number of rows processed.
    """
    log.info("=" * 70)
    log.info("FAZA 1 — Import firme din OD_FIRME.CSV")
    log.info("=" * 70)

    # Ensure we have a local CSV file
    csv_path = Path(csv_local) if csv_local else LOG_DIR / "od_firme.csv"
    if not csv_path.exists():
        await _download_csv(csv_url, csv_path)
    else:
        log.info(f"  Folosesc fișier local: {csv_path} ({csv_path.stat().st_size / 1024 / 1024:.1f} MB)")

    INSERT_SQL = """
        INSERT INTO companies (
            cui, denumire, j_nr, forma_juridica, stare,
            data_infiintare, judet, localitate, cod_postal, adresa_completa,
            platitor_tva, tva_la_incasare, split_tva, inactiv_fiscal,
            has_insolvency, has_litigation, has_debts,
            has_seap_contracts, has_eu_projects, has_trademarks,
            data_quality_score, data_sources
        ) VALUES (
            $1,  LEFT($2::text, 499),  LEFT($3::text, 20),  LEFT($4::text, 10),  LEFT($5::text, 20),
            $6,  LEFT($7::text, 50),  LEFT($8::text, 100),  LEFT($9::text, 10),  $10,
            false, false, false, false,
            false, false, false,
            false, false, false,
            40, '{"onrc_csv": true}'::jsonb
        )
        ON CONFLICT (cui) DO NOTHING
    """

    BATCH_SIZE = 2000
    batch: list[tuple] = []
    rows_processed = 0
    rows_inserted  = 0
    rows_skipped   = 0
    t_start = time.time()

    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="^")
        for row_num, row in enumerate(reader, start=1):

            # Skip already-processed rows when resuming
            if row_num <= resume_from:
                if row_num % 200_000 == 0:
                    log.info(f"  Resume: sărind rândul {row_num:,}...")
                continue

            if limit and rows_processed >= limit:
                break

            cui = _parse_cui(row.get("CUI", ""))
            if cui is None:
                rows_skipped += 1
                continue

            # Strip BOM from DENUMIRE key (csv.DictReader with utf-8-sig should handle it,
            # but be defensive)
            denumire = (
                row.get("DENUMIRE")
                or row.get("\ufeffDENUMIRE")
                or ""
            ).strip()
            if not denumire:
                rows_skipped += 1
                continue

            j_nr = _clean(row.get("COD_INMATRICULARE", ""), 20)
            forma_jur = _map_forma(row.get("FORMA_JURIDICA", ""))
            data_inf  = _parse_date_dmy(row.get("DATA_INMATRICULARE", ""))
            judet     = _clean(row.get("ADR_JUDET", ""), 50)
            loc       = _clean(row.get("ADR_LOCALITATE", ""), 100)
            cod_post  = _clean((row.get("ADR_COD_POSTAL") or "").strip(), 10)
            adresa    = _build_address(row)

            batch.append((
                cui, denumire[:499], j_nr, forma_jur, "ACTIVA",
                data_inf, judet[:50] if judet else None,
                loc[:100] if loc else None,
                cod_post[:10] if cod_post else None,
                adresa[:1000] if adresa else None,
            ))
            rows_processed += 1

            if len(batch) >= BATCH_SIZE:
                async with pool.acquire() as conn:
                    await conn.executemany(INSERT_SQL, batch)
                rows_inserted += len(batch)
                batch.clear()

                if rows_processed % 100_000 == 0:
                    elapsed = time.time() - t_start
                    rate = rows_processed / elapsed
                    log.info(
                        f"  Rând {rows_processed:,} | Inserate ~{rows_inserted:,} "
                        f"| {rate:.0f} rând/sec"
                    )
                    _save_progress({
                        "phase1_done": False, "phase1_rows": rows_processed,
                        "phase2_done": False, "phase2_last_cui": 0,
                        "phase3_done": False, "phase3_rows": 0,
                    })

    # Flush remaining
    if batch:
        async with pool.acquire() as conn:
            await conn.executemany(INSERT_SQL, batch)
        rows_inserted += len(batch)

    elapsed = time.time() - t_start
    log.info(
        f"[Faza 1] COMPLET în {elapsed / 60:.1f} min | "
        f"Procesate: {rows_processed:,} | Inserate ~{rows_inserted:,} | Sărite: {rows_skipped:,}"
    )
    return rows_processed


# ════════════════════════════════════════════════════════════════════════════════
# FAZA 2 — ANAF enrichment (TVA, CAEN, inactiv_fiscal)
# ════════════════════════════════════════════════════════════════════════════════

async def phase2_anaf_enrichment(
    pool: asyncpg.Pool,
    last_cui: int,
    limit: int,
) -> int:
    """
    Enrich companies with ANAF fiscal data.
    Batches of 500 CUIs, ~1 request/second.
    Returns number of companies updated.
    """
    log.info("=" * 70)
    log.info("FAZA 2 — Enrichment ANAF (TVA, CAEN, stare fiscală)")
    log.info("=" * 70)

    async with pool.acquire() as conn:
        if limit:
            rows = await conn.fetch(
                "SELECT cui FROM companies WHERE cui > $1 ORDER BY cui LIMIT $2",
                last_cui, limit,
            )
        else:
            rows = await conn.fetch(
                "SELECT cui FROM companies WHERE cui > $1 ORDER BY cui",
                last_cui,
            )

    cuis = [r["cui"] for r in rows]
    total = len(cuis)
    log.info(f"  {total:,} CUI-uri de procesat")

    today = date.today().strftime("%Y-%m-%d")
    updated = 0
    t_start = time.time()

    for i in range(0, total, ANAF_BATCH):
        batch_cuis = cuis[i: i + ANAF_BATCH]
        payload = [{"cui": c, "data": today} for c in batch_cuis]

        try:
            # Submit
            async with httpx.AsyncClient(timeout=30.0) as client:
                submit = await client.post(ANAF_URL, json=payload)
                submit.raise_for_status()
                sub_data = submit.json()

            if sub_data.get("cod") != 200:
                log.warning(f"  ANAF submit error batch {i // ANAF_BATCH + 1}: {sub_data}")
                await asyncio.sleep(ANAF_DELAY)
                continue

            corr_id = sub_data.get("correlationId")

            # Poll (up to 6 attempts with backoff)
            found = None
            for attempt in range(6):
                await asyncio.sleep(2.0 * (attempt + 1))
                try:
                    async with httpx.AsyncClient(timeout=30.0) as pc:
                        poll = await pc.get(ANAF_URL, params={"id": corr_id})
                        if poll.status_code == 200:
                            pd = poll.json()
                            if pd.get("cod") == 200:
                                found = pd.get("found", [])
                                break
                except Exception as pe:
                    log.debug(f"  Poll attempt {attempt + 1} failed: {pe}")

            if found:
                n = await _apply_anaf_updates(pool, found)
                updated += n

            # Save progress every 50 batches
            if (i // ANAF_BATCH + 1) % 50 == 0:
                last = batch_cuis[-1]
                pct = (i + len(batch_cuis)) / total * 100
                elapsed = time.time() - t_start
                rate = (i + len(batch_cuis)) / elapsed
                log.info(
                    f"  ANAF: {i + len(batch_cuis):,}/{total:,} ({pct:.1f}%) "
                    f"| Updated: {updated:,} | {rate:.0f} CUI/sec"
                )
                _save_progress({
                    "phase1_done": True, "phase1_rows": 0,
                    "phase2_done": False, "phase2_last_cui": last,
                    "phase3_done": False, "phase3_rows": 0,
                })

        except Exception as e:
            log.error(f"  Eroare batch ANAF {i // ANAF_BATCH + 1}: {e}")
            await asyncio.sleep(5.0)

        await asyncio.sleep(ANAF_DELAY)

    elapsed = time.time() - t_start
    log.info(
        f"[Faza 2] COMPLET în {elapsed / 60:.1f} min | "
        f"Actualizate: {updated:,}/{total:,}"
    )
    return updated


async def _apply_anaf_updates(pool: asyncpg.Pool, found: list[dict]) -> int:
    """Apply ANAF response data to companies table."""
    UPDATE_SQL = """
        UPDATE companies SET
            platitor_tva     = $1,
            tva_la_incasare  = $2,
            split_tva        = $3,
            inactiv_fiscal   = $4,
            caen_principal   = COALESCE($5, caen_principal),
            judet            = COALESCE($6, judet),
            localitate       = COALESCE($7, localitate),
            cod_postal       = COALESCE($8, cod_postal),
            telefon          = COALESCE($10, telefon),
            fax              = COALESCE($11, fax),
            capital_social   = COALESCE($12, capital_social),
            data_infiintare  = COALESCE(data_infiintare, $13),
            data_quality_score = GREATEST(data_quality_score, 60),
            data_sources     = replace(replace(data_sources, '{"onrc_csv": true}', '{"onrc_csv": true, "anaf": true}'), '{"onrc_csv": true, "anaf": true, "anaf": true}', '{"onrc_csv": true, "anaf": true}'),
            updated_at       = NOW()
        WHERE cui = $9
    """
    updates = []
    for raw in found:
        gen     = raw.get("date_generale", {})
        tva     = raw.get("inregistrare_scop_Tva", {})
        tva_inc = raw.get("inregistrare_RTVAI", {})
        split   = raw.get("inregistrare_SplitTVA", {})
        inactiv = raw.get("stare_inactiv", {})
        sediu   = raw.get("adresa_sediu_social", {})

        cui = gen.get("cui")
        if not cui:
            continue

        caen       = _clean(gen.get("cod_CAEN") or gen.get("caen"), 4)
        judet      = _clean(sediu.get("sdenumire_Judet") or gen.get("judet"), 50)
        localitate = _clean(sediu.get("sdenumire_Localitate") or gen.get("localitate"), 100)
        cod_post   = _clean((sediu.get("scod_Postal") or gen.get("codPostal") or "").strip(), 10)
        telefon    = _clean(gen.get("telefon"), 30)
        fax        = _clean(gen.get("fax"), 30)
        # capital_social poate fi float sau string
        cap_raw    = gen.get("capitalSocial") or gen.get("capital_social")
        try:
            capital = float(cap_raw) if cap_raw not in (None, "", "0", 0) else None
        except (ValueError, TypeError):
            capital = None
        # dataInregistrare = data înregistrare fiscală (YYYY-MM-DD)
        data_inreg = _parse_date_dmy(gen.get("dataInregistrare") or gen.get("data_inregistrare") or "")

        updates.append((
            bool(tva.get("scpTVA", False)),
            bool(tva_inc.get("statusTvaIncasare", False)),
            bool(split.get("statusSplitTVA", False)),
            bool(inactiv.get("statusInactivi", False)),
            caen, judet, localitate, cod_post,
            cui,
            telefon, fax, capital, data_inreg,
        ))

    if not updates:
        return 0
    async with pool.acquire() as conn:
        await conn.executemany(UPDATE_SQL, updates)
    return len(updates)


# ════════════════════════════════════════════════════════════════════════════════
# FAZA 4 — Enrichment din OD_FIRME.CSV: data_infiintare, website, euid
# ════════════════════════════════════════════════════════════════════════════════

async def phase4_enrich_from_csv(
    pool: asyncpg.Pool,
    csv_local: Optional[str],
    limit: int,
) -> int:
    """
    Re-reads OD_FIRME.CSV and updates:
      - data_infiintare (was NULL due to DD.MM.YYYY format bug)
      - website (new column)
      - euid (European unique identifier)
    Returns number of rows updated.
    """
    log.info("=" * 70)
    log.info("FAZA 4 — Enrichment date_infiintare + website din OD_FIRME.CSV")
    log.info("=" * 70)

    csv_path = Path(csv_local) if csv_local else LOG_DIR / "od_firme.csv"
    if not csv_path.exists():
        log.error(f"  CSV nu există: {csv_path}")
        return 0
    log.info(f"  Fișier: {csv_path} ({csv_path.stat().st_size / 1024 / 1024:.0f} MB)")

    UPDATE_SQL = """
        UPDATE companies SET
            data_infiintare = COALESCE(data_infiintare, $1::date),
            website         = COALESCE(website, $2::varchar),
            euid            = COALESCE(euid, $3::varchar),
            updated_at      = NOW()
        WHERE cui = $4
    """

    BATCH_SIZE = 5000
    batch: list[tuple] = []  # (data_infiintare, website, euid, cui)
    processed = 0
    updated   = 0
    t_start   = time.time()

    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="^")
        for row in reader:
            if limit and processed >= limit:
                break

            cui = _parse_cui(row.get("CUI", ""))
            if not cui:
                continue

            data_inf = _parse_date_dmy(row.get("DATA_INMATRICULARE", ""))
            website  = _clean(row.get("WEB", ""), 500)
            # Basic URL validation
            if website and not website.startswith(("http", "www", "HTTP")):
                website = None
            euid = _clean(row.get("EUID", ""), 40)

            if data_inf is None and website is None and euid is None:
                continue

            batch.append((data_inf, website, euid, cui))
            processed += 1

            if len(batch) >= BATCH_SIZE:
                async with pool.acquire() as conn:
                    result = await conn.execute(UPDATE_SQL, *batch[0]) if len(batch) == 1 else None
                    await conn.executemany(UPDATE_SQL, batch)
                updated += len(batch)
                batch.clear()

                if processed % 500_000 == 0:
                    elapsed = time.time() - t_start
                    log.info(
                        f"  Procesate: {processed:,} | Actualizate ~{updated:,}"
                        f" | {processed / elapsed:.0f} rând/sec"
                    )

    if batch:
        async with pool.acquire() as conn:
            await conn.executemany(UPDATE_SQL, batch)
        updated += len(batch)

    elapsed = time.time() - t_start
    log.info(
        f"[Faza 4] COMPLET în {elapsed / 60:.1f} min | "
        f"Procesate: {processed:,} | Actualizate ~{updated:,}"
    )
    return updated


# ════════════════════════════════════════════════════════════════════════════════
# FAZA 3 — Import reprezentanți legali din OD_REPREZENTANTI_LEGALI.CSV
# ════════════════════════════════════════════════════════════════════════════════

async def phase3_import_reprezentanti(
    pool: asyncpg.Pool,
    csv_url: str,
    csv_local: Optional[str],
    limit: int,
) -> int:
    """
    Import administrators, associates, and auditors from ONRC open data.
    Links via j_nr (COD_INMATRICULARE) → company_id.
    Returns number of rows processed.
    """
    log.info("=" * 70)
    log.info("FAZA 3 — Import reprezentanți legali (OD_REPREZENTANTI_LEGALI.CSV)")
    log.info("=" * 70)

    # Load j_nr → company_id map from DB
    log.info("  Încarc maparea J-nr → company_id din DB...")
    async with pool.acquire() as conn:
        jnr_rows = await conn.fetch(
            "SELECT id, j_nr FROM companies WHERE j_nr IS NOT NULL"
        )
    jnr_map: dict[str, int] = {r["j_nr"]: r["id"] for r in jnr_rows}
    log.info(f"  {len(jnr_map):,} firme cu J-nr încărcate")

    csv_path = Path(csv_local) if csv_local else LOG_DIR / "od_reprezentanti_legali.csv"
    if not csv_path.exists():
        await _download_csv(csv_url, csv_path)
    else:
        log.info(f"  Folosesc fișier local: {csv_path}")

    INSERT_SQL = """
        INSERT INTO company_persons (
            company_id, tip, nume_complet, data_start, activ
        ) VALUES ($1, $2, $3, $4, true)
        ON CONFLICT DO NOTHING
    """

    BATCH_SIZE = 3000
    batch: list[tuple] = []
    processed = 0
    inserted  = 0
    skipped   = 0
    t_start   = time.time()

    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="^")
        for row in reader:
            if limit and processed >= limit:
                break

            j_nr     = _clean(row.get("COD_INMATRICULARE") or row.get("\ufeffCOD_INMATRICULARE"), 20)
            calitate = (row.get("CALITATE") or "").strip().lower()
            persoana = _clean(row.get("PERSOANA_IMPUTERNICITA", ""), 200)

            if not j_nr or not persoana:
                skipped += 1
                continue

            company_id = jnr_map.get(j_nr)
            if company_id is None:
                skipped += 1
                continue

            tip = _map_calitate(calitate)
            if tip is None:
                skipped += 1
                continue

            data_start = _parse_date_dmy(row.get("DATA_NASTERE", ""))
            batch.append((company_id, tip, persoana, data_start))
            processed += 1

            if len(batch) >= BATCH_SIZE:
                async with pool.acquire() as conn:
                    await conn.executemany(INSERT_SQL, batch)
                inserted += len(batch)
                batch.clear()

                if processed % 500_000 == 0:
                    elapsed = time.time() - t_start
                    log.info(
                        f"  Procesate: {processed:,} | Inserate ~{inserted:,} "
                        f"| {processed / elapsed:.0f} rând/sec"
                    )

    if batch:
        async with pool.acquire() as conn:
            await conn.executemany(INSERT_SQL, batch)
        inserted += len(batch)

    elapsed = time.time() - t_start
    log.info(
        f"[Faza 3] COMPLET în {elapsed / 60:.1f} min | "
        f"Procesate: {processed:,} | Inserate ~{inserted:,} | Sărite: {skipped:,}"
    )
    return processed


# ════════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════════

def _print_summary(pool_dsn_host: str):
    log.info("")
    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info("║   ESTIMARE TIMP TOTAL (toate fazele, server cu 4 CPU)    ║")
    log.info("╠══════════════════════════════════════════════════════════╣")
    log.info("║  Faza 1 — CSV import 2.9M firme       ~ 30-60 minute    ║")
    log.info("║  Faza 2 — ANAF enrichment 2.9M CUI    ~ 2-3 ore         ║")
    log.info("║  Faza 3 — Reprezentanți legali         ~ 10-20 minute   ║")
    log.info("║  TOTAL                                 ~ 3-4 ore        ║")
    log.info("╠══════════════════════════════════════════════════════════╣")
    log.info("║  Log detaliat:                                           ║")
    log.info(f"║    {str(LOG_FILE):<56}║")
    log.info("║  Progress tracker:                                       ║")
    log.info(f"║    {str(PROGRESS_FILE):<56}║")
    log.info("║                                                          ║")
    log.info("║  Oprire curată: Ctrl+C (scriptul e rezumabil cu --resume)║")
    log.info("╚══════════════════════════════════════════════════════════╝")
    log.info("")


async def main():
    parser = argparse.ArgumentParser(
        description="Bulk import firme ONRC open data + enrichment ANAF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--only", type=int, choices=[1, 2, 3, 4],
        help="Rulează doar faza specificată (1=CSV, 2=ANAF, 3=Reprezentanți, 4=Enrich CSV)"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Număr maxim de înregistrări per fază (0=toate)"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Continuă de unde s-a oprit (citește progress din logs/)"
    )
    parser.add_argument(
        "--firme-csv", metavar="PATH",
        help="Folosește fișier OD_FIRME.CSV local (evită descărcarea)"
    )
    parser.add_argument(
        "--reprez-csv", metavar="PATH",
        help="Folosește fișier OD_REPREZENTANTI_LEGALI.CSV local"
    )
    parser.add_argument(
        "--firme-url", default=ONRC_FIRME_URL,
        help="URL alternativ pentru OD_FIRME.CSV"
    )
    parser.add_argument(
        "--reprez-url", default=ONRC_REPREZ_URL,
        help="URL alternativ pentru OD_REPREZENTANTI_LEGALI.CSV"
    )
    args = parser.parse_args()

    log.info("██████████████████████████████████████████████████████████████████")
    log.info("  RomBiz — Bulk Import ONRC + ANAF")
    log.info(f"  Pornit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("██████████████████████████████████████████████████████████████████")

    run_phase = {1: True, 2: True, 3: True, 4: True}
    if args.only:
        run_phase = {1: False, 2: False, 3: False, 4: False, args.only: True}

    progress = _load_progress() if args.resume else {
        "phase1_done": False, "phase1_rows": 0,
        "phase2_done": False, "phase2_last_cui": 0,
        "phase3_done": False, "phase3_rows": 0,
        "phase4_done": False,
    }

    _print_summary("")
    pool = await get_pool()

    t_global = time.time()

    try:
        # ── Faza 1 ──────────────────────────────────────────────────────────
        if run_phase[1]:
            if args.resume and progress.get("phase1_done"):
                log.info("[Faza 1] Deja completată — sărit (--resume).")
            else:
                resume_row = progress.get("phase1_rows", 0) if args.resume else 0
                rows = await phase1_import_firme(
                    pool,
                    csv_url=args.firme_url,
                    csv_local=args.firme_csv,
                    limit=args.limit,
                    resume_from=resume_row,
                )
                progress["phase1_done"] = True
                progress["phase1_rows"] = rows
                _save_progress(progress)

        # ── Faza 2 ──────────────────────────────────────────────────────────
        if run_phase[2]:
            if args.resume and progress.get("phase2_done"):
                log.info("[Faza 2] Deja completată — sărit (--resume).")
            else:
                last_cui = progress.get("phase2_last_cui", 0) if args.resume else 0
                await phase2_anaf_enrichment(pool, last_cui=last_cui, limit=args.limit)
                progress["phase2_done"] = True
                _save_progress(progress)

        # ── Faza 3 ──────────────────────────────────────────────────────────
        if run_phase[3]:
            if args.resume and progress.get("phase3_done"):
                log.info("[Faza 3] Deja completată — sărit (--resume).")
            else:
                await phase3_import_reprezentanti(
                    pool,
                    csv_url=args.reprez_url,
                    csv_local=args.reprez_csv,
                    limit=args.limit,
                )
                progress["phase3_done"] = True
                _save_progress(progress)

        # ── Faza 4 ──────────────────────────────────────────────────────────
        if run_phase[4]:
            if args.resume and progress.get("phase4_done"):
                log.info("[Faza 4] Deja completată — sărit (--resume).")
            else:
                await phase4_enrich_from_csv(
                    pool,
                    csv_local=args.firme_csv,
                    limit=args.limit,
                )
                progress["phase4_done"] = True
                _save_progress(progress)

        elapsed_total = time.time() - t_global
        log.info("=" * 70)
        log.info(f"IMPORT COMPLET în {elapsed_total / 60:.1f} minute")
        log.info("=" * 70)

    except KeyboardInterrupt:
        log.info("")
        log.info("Oprit de utilizator (Ctrl+C). Progresul a fost salvat.")
        log.info(f"Continuă cu: python3 scripts/bulk_import_onrc.py --resume")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
