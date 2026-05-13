#!/usr/bin/env python3
"""
import_firme_noi.py
==================
Script de import zilnic pentru firme nou înregistrate la ONRC.

Strategie:
  1. Populează new_companies_feed pentru firmele deja în DB cu data_infiintare = ieri
     (acoperă companiile care au intrat prin bulk import dar nu au feed entry)
  2. Scanează CUI-uri noi prin ANAF v8 pornind de la ultimul CUI secvențial cunoscut
     → inserează în companies + new_companies_feed firmele descoperite

Checkpoint: logs/firme_noi_checkpoint.txt  (salvează ultimul CUI scanat)
Log:        logs/firme_noi.log

Utilizare:
  python3 scripts/import_firme_noi.py
  python3 scripts/import_firme_noi.py --date 2026-05-05   # backfill zi specifică
  python3 scripts/import_firme_noi.py --scan-only          # doar scanare CUI noi
  python3 scripts/import_firme_noi.py --feed-only          # doar populare feed din DB
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import asyncpg

# ── Configurare ────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

CHECKPOINT_FILE = LOG_DIR / "firme_noi_checkpoint.txt"
LOG_FILE = LOG_DIR / "firme_noi.log"

DSN = "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db"

ANAF_URL = "https://webservicesp.anaf.ro/AsynchWebService/api/v8/ws/tva"
ANAF_BATCH_SIZE = 500          # limita ANAF per request
ANAF_POLL_SLEEP = 4.0          # secunde de așteptat înainte de poll
ANAF_RATE_SLEEP = 1.2          # pauză între batch-uri (anti-rate-limit)
ANAF_MAX_RETRIES = 3

# CUI-uri > acest prag sunt outlieri (PJ strǎine etc.) - ignorǎm la scanare
MAX_SEQUENTIAL_CUI = 100_000_000

# Dacă avem X CUI-uri consecutive inexistente în ANAF → probabil am depășit maximul curent
MAX_CONSECUTIVE_NOTFOUND = 2000

# Câte CUI-uri scanăm per rulare (limită pentru a nu depăși durata unui cron)
MAX_CUIS_PER_RUN = 50_000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── ANAF helpers ───────────────────────────────────────────────────────────────

def _anaf_post(cuis: list[int], today_str: str) -> dict:
    payload = json.dumps([{"cui": c, "data": today_str} for c in cuis]).encode("utf-8")
    req = urllib.request.Request(
        ANAF_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def _anaf_poll(correlation_id: str) -> dict:
    url = f"{ANAF_URL}?id={correlation_id}"
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read())


def anaf_batch_query(cuis: list[int], today_str: str) -> dict:
    """Trimite un batch de CUI-uri la ANAF și returnează răspunsul complet."""
    for attempt in range(1, ANAF_MAX_RETRIES + 1):
        try:
            resp = _anaf_post(cuis, today_str)
            cid = resp.get("correlationId")
            if not cid:
                raise ValueError(f"No correlationId in response: {resp}")
            time.sleep(ANAF_POLL_SLEEP)
            result = _anaf_poll(cid)
            return result
        except urllib.error.HTTPError as e:
            log.warning(f"ANAF HTTP {e.code} (attempt {attempt}/{ANAF_MAX_RETRIES})")
            if attempt < ANAF_MAX_RETRIES:
                time.sleep(5 * attempt)
        except Exception as e:
            log.warning(f"ANAF error (attempt {attempt}/{ANAF_MAX_RETRIES}): {e}")
            if attempt < ANAF_MAX_RETRIES:
                time.sleep(5 * attempt)
    log.error(f"ANAF batch failed after {ANAF_MAX_RETRIES} retries")
    return {"found": [], "notfound": list(cuis)}


# ── Parsare răspuns ANAF ────────────────────────────────────────────────────────

def _extract_company_data(item: dict) -> dict | None:
    """Extrage câmpurile relevante dintr-un item ANAF found."""
    g = item.get("date_generale", {})
    cui = g.get("cui")
    if not cui:
        return None

    denumire = g.get("denumire", "").strip() or None
    if not denumire:
        return None

    # Adresă din adresa_sediu_social (mai structurată)
    addr = item.get("adresa_sediu_social", {}) or {}
    judet = (addr.get("sdenumire_Judet") or "").strip() or None
    localitate = (addr.get("sdenumire_Localitate") or "").strip() or None
    strada = addr.get("sdenumire_Strada") or ""
    nr = addr.get("snumar_Strada") or ""
    bloc = addr.get("sdetalii_Adresa") or ""
    cod_postal = (addr.get("scod_Postal") or "").strip() or None

    adresa_parts = []
    if strada:
        adresa_parts.append(f"Str. {strada}")
    if nr:
        adresa_parts.append(f"Nr. {nr}")
    if bloc:
        adresa_parts.append(bloc)
    if localitate:
        adresa_parts.append(localitate)
    if judet:
        adresa_parts.append(f"Jud. {judet}")
    adresa_completa = ", ".join(adresa_parts) or None

    # Data înregistrare (format: "DD.MM.YYYY" sau "YYYY-MM-DD")
    data_str = g.get("data_inregistrare") or g.get("data_infiintare") or ""
    data_infiintare = None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            data_infiintare = datetime.strptime(data_str.strip(), fmt).date()
            break
        except (ValueError, AttributeError):
            pass

    # Cod CAEN
    caen = (g.get("cod_CAEN") or "").strip() or None
    if caen:
        caen = caen[:4]  # max 4 chars

    # Forma juridică (normalizăm)
    stare_inreg = (g.get("stare_inregistrare") or "").strip()
    if "ACTIV" in stare_inreg.upper():
        stare = "ACTIVA"
    elif "RADIAT" in stare_inreg.upper():
        stare = "RADIATA"
    else:
        stare = "ACTIVA"

    # Contact & fiscal
    telefon = (g.get("telefon") or "").strip() or None
    fax = (g.get("fax") or "").strip() or None
    status_efact = bool(g.get("statusRO_e_Factura", False))

    tva_info = item.get("inregistrare_scop_Tva", {}) or {}
    perioade = tva_info.get("perioade_TVA") or []
    perioade = [p for p in perioade if p.get("data_inceput_ScpTVA")]
    platitor_tva = bool(tva_info.get("scpTVA", False)) or len(perioade) > 0

    inactiv = bool((item.get("stare_inactiv") or {}).get("dataInactivare"))
    split_tva = bool((item.get("inregistrare_SplitTVA") or {}).get("dataInregistrare"))
    tva_incasare = bool((item.get("inregistrare_RTVAI") or {}).get("dataInregistrareRTVAI"))

    return {
        "cui": cui,
        "denumire": denumire,
        "stare": stare,
        "data_infiintare": data_infiintare,
        "caen_principal": caen,
        "judet": judet,
        "localitate": localitate,
        "adresa_completa": adresa_completa,
        "cod_postal": cod_postal,
        "telefon": telefon,
        "fax": fax,
        "platitor_tva": platitor_tva,
        "tva_la_incasare": tva_incasare,
        "split_tva": split_tva,
        "inactiv_fiscal": inactiv,
        "status_ro_efactura": status_efact,
        "tva_perioade": json.dumps(perioade, ensure_ascii=False) if perioade else None,
    }


# ── DB helpers ─────────────────────────────────────────────────────────────────

async def feed_from_db(conn: asyncpg.Connection, target_date: date) -> int:
    """
    Inserează în new_companies_feed firmele din DB cu data_infiintare = target_date
    care nu sunt deja în feed.
    Returnează numărul de înregistrări inserate.
    """
    rows = await conn.fetch(
        """
        INSERT INTO new_companies_feed (company_id, registration_date, feed_date, sursa, is_notified)
        SELECT c.id, c.data_infiintare, CURRENT_DATE, 'db_scan', FALSE
        FROM companies c
        WHERE c.data_infiintare = $1
          AND NOT EXISTS (
              SELECT 1 FROM new_companies_feed f WHERE f.company_id = c.id
          )
        RETURNING company_id
        """,
        target_date,
    )
    return len(rows)


async def insert_company(conn: asyncpg.Connection, d: dict) -> int | None:
    """
    Inserează o firmă nouă în companies. Returnează id-ul nou sau None dacă există deja.
    Folosim ON CONFLICT DO NOTHING pe CUI.
    """
    row = await conn.fetchrow(
        """
        INSERT INTO companies (
            cui, denumire, stare, data_infiintare, caen_principal,
            judet, localitate, adresa_completa, cod_postal,
            telefon, fax,
            platitor_tva, tva_la_incasare, split_tva, inactiv_fiscal,
            status_ro_efactura, tva_perioade,
            has_insolvency, has_litigation, has_debts,
            has_seap_contracts, has_eu_projects, has_trademarks,
            data_quality_score, data_sources
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9,
            $10, $11,
            $12, $13, $14, $15,
            $16, $17::jsonb,
            FALSE, FALSE, FALSE,
            FALSE, FALSE, FALSE,
            20, '{}'::jsonb
        )
        ON CONFLICT (cui) DO NOTHING
        RETURNING id
        """,
        d["cui"], d["denumire"], d["stare"], d["data_infiintare"], d["caen_principal"],
        d["judet"], d["localitate"], d["adresa_completa"], d["cod_postal"],
        d["telefon"], d["fax"],
        d["platitor_tva"], d["tva_la_incasare"], d["split_tva"], d["inactiv_fiscal"],
        d["status_ro_efactura"], d["tva_perioade"],
    )
    return row["id"] if row else None


async def insert_feed(conn: asyncpg.Connection, company_id: int, reg_date: date | None) -> None:
    """Inserează în new_companies_feed dacă nu există deja."""
    if reg_date is None:
        reg_date = date.today()
    await conn.execute(
        """
        INSERT INTO new_companies_feed (company_id, registration_date, feed_date, sursa, is_notified)
        VALUES ($1, $2, CURRENT_DATE, 'anaf_scan', FALSE)
        ON CONFLICT DO NOTHING
        """,
        company_id, reg_date,
    )


# ── Checkpoint ─────────────────────────────────────────────────────────────────

def load_checkpoint() -> int | None:
    if CHECKPOINT_FILE.exists():
        try:
            val = int(CHECKPOINT_FILE.read_text().strip())
            return val
        except ValueError:
            pass
    return None


def save_checkpoint(cui: int) -> None:
    CHECKPOINT_FILE.write_text(str(cui))


# ── Pasul 2: Scanare CUI-uri noi ──────────────────────────────────────────────

async def scan_new_cuis(conn: asyncpg.Connection, today_str: str) -> tuple[int, int]:
    """
    Scanează CUI-uri noi pornind de la checkpoint (sau max CUI secvențial din DB).
    Returnează (inserted_companies, feed_entries).
    """
    # Determinăm CUI de start
    checkpoint = load_checkpoint()
    if checkpoint is not None:
        start_cui = checkpoint + 1
        log.info(f"Checkpoint găsit: start CUI = {start_cui:,}")
    else:
        # Pornim de la max CUI din ultima zi de înregistrare din DB
        # (companiile noi sunt secvențiale față de ultima zi importată)
        row = await conn.fetchrow(
            """
            SELECT MAX(c.cui) AS max_cui
            FROM companies c
            WHERE c.data_infiintare = (
                SELECT MAX(data_infiintare) FROM companies
                WHERE data_infiintare IS NOT NULL
                  AND data_infiintare <= CURRENT_DATE
            )
            """
        )
        max_db_cui = row["max_cui"] or 1_000_000
        start_cui = max_db_cui + 1
        log.info(
            f"Fără checkpoint. Max CUI din ultima zi înregistrare = {max_db_cui:,}. "
            f"Start scanare = {start_cui:,}"
        )

    # Obținem CUI-urile deja existente în DB (pentru evitarea re-inserării)
    # Nu le încărcăm toate — verificăm per batch cu query
    total_inserted = 0
    total_feed = 0
    consecutive_notfound = 0
    scanned = 0

    cui = start_cui

    while scanned < MAX_CUIS_PER_RUN:
        batch_cuis = list(range(cui, cui + ANAF_BATCH_SIZE))
        scanned += len(batch_cuis)
        cui += ANAF_BATCH_SIZE

        result = anaf_batch_query(batch_cuis, today_str)
        found = result.get("found", [])
        not_found_count = len(result.get("notfound", batch_cuis)) + (ANAF_BATCH_SIZE - len(found) - len(result.get("notfound", [])))

        if not found:
            consecutive_notfound += ANAF_BATCH_SIZE
            if consecutive_notfound >= MAX_CONSECUTIVE_NOTFOUND:
                log.info(
                    f"Stop: {consecutive_notfound} CUI-uri consecutive inexistente. "
                    f"Ultimul CUI scanat: {cui - 1:,}"
                )
                save_checkpoint(cui - 1)
                break
        else:
            consecutive_notfound = 0
            log.info(
                f"CUI range {batch_cuis[0]:,}-{batch_cuis[-1]:,}: "
                f"{len(found)} găsite, {not_found_count} negăsite"
            )

            # Verificăm care CUI-uri există deja în DB
            found_cuis = [item.get("date_generale", {}).get("cui") for item in found if item.get("date_generale", {}).get("cui")]
            existing = await conn.fetch(
                "SELECT cui, id FROM companies WHERE cui = ANY($1::int[])",
                found_cuis,
            )
            existing_map = {r["cui"]: r["id"] for r in existing}

            for item in found:
                d = _extract_company_data(item)
                if not d:
                    continue

                company_id = existing_map.get(d["cui"])
                if company_id is None:
                    # Firma nouă — inserăm în companies
                    new_id = await insert_company(conn, d)
                    if new_id:
                        company_id = new_id
                        total_inserted += 1
                        log.info(
                            f"  [NOU] CUI {d['cui']} | {d['denumire'][:50]} | "
                            f"{d['judet']} | data: {d['data_infiintare']}"
                        )

                if company_id:
                    await insert_feed(conn, company_id, d.get("data_infiintare"))
                    total_feed += 1

        save_checkpoint(cui - 1)
        time.sleep(ANAF_RATE_SLEEP)

    log.info(
        f"Scanare completă: {scanned:,} CUI-uri testate, "
        f"{total_inserted} firme noi inserate, {total_feed} feed entries create"
    )
    return total_inserted, total_feed


# ── Main ───────────────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> None:
    log.info("=" * 60)
    log.info("import_firme_noi START")
    log.info(f"Mode: feed_only={args.feed_only}, scan_only={args.scan_only}")

    today = date.today()
    today_str = today.isoformat()

    # Data pentru pasul 1 (feed din DB)
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            log.error(f"Format dată invalid: {args.date}. Folosiți YYYY-MM-DD.")
            sys.exit(1)
    else:
        target_date = today - timedelta(days=1)

    conn = await asyncpg.connect(DSN)

    try:
        # ── Pasul 1: Populare feed din firme deja în DB ──────────────────────
        if not args.scan_only:
            log.info(f"[Pas 1] Populare feed pentru data_infiintare = {target_date}")
            inserted_from_db = await feed_from_db(conn, target_date)
            log.info(f"[Pas 1] {inserted_from_db} intrări adăugate în feed din DB")

        # ── Pasul 2: Scanare CUI-uri noi ────────────────────────────────────
        if not args.feed_only:
            log.info("[Pas 2] Scanare CUI-uri noi prin ANAF v8")
            new_companies, feed_entries = await scan_new_cuis(conn, today_str)
            log.info(f"[Pas 2] {new_companies} firme noi | {feed_entries} feed entries")

        # ── Sumar final ─────────────────────────────────────────────────────
        total_feed = await conn.fetchval("SELECT COUNT(*) FROM new_companies_feed")
        today_feed = await conn.fetchval(
            "SELECT COUNT(*) FROM new_companies_feed WHERE feed_date = CURRENT_DATE"
        )
        log.info(f"TOTAL în new_companies_feed: {total_feed:,} | Adăugate azi: {today_feed:,}")

    finally:
        await conn.close()

    log.info("import_firme_noi DONE")
    log.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import firme nou înregistrate")
    parser.add_argument(
        "--date",
        help="Data pentru feed din DB (YYYY-MM-DD). Default: ieri",
        default=None,
    )
    parser.add_argument(
        "--feed-only",
        action="store_true",
        help="Doar populează feed din firmele existente în DB (fără scanare ANAF)",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Doar scanează CUI-uri noi prin ANAF (fără feed din DB)",
    )
    args = parser.parse_args()

    asyncio.run(main(args))
