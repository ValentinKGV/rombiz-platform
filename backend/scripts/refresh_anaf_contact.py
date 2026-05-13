#!/usr/bin/env python3
"""
Refresh ANAF contact data for ALL companies.

Actualizează pentru fiecare firmă din DB:
  - telefon, fax
  - status_ro_efactura
  - tva_perioade (JSONB)
  - stare_inregistrare (din ANAF, mai detaliată)

Rate: 1 request/sec, batch 500 CUI-uri => ~3.85M / 500 = ~7711 req => ~2-4 ore.
Checkpoint salvat în logs/anaf_contact_checkpoint.txt (ultima pagina procesată).

Rulare:
    nohup python scripts/refresh_anaf_contact.py >> logs/refresh_anaf_contact.log 2>&1 &
"""
import asyncio
import asyncpg
import json
import logging
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

DSN = "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db"
ANAF_URL = "https://webservicesp.anaf.ro/AsynchWebService/api/v8/ws/tva"
BATCH_SIZE = 500       # limita ANAF
DB_CHUNK = 10_000      # câte CUI-uri citim din DB odată
POLL_DELAY = 3.0       # secunde așteptare după submit
MAX_POLL = 5           # încercări de polling
RATE_SLEEP = 1.1       # secunde între request-uri (ANAF: 1 req/sec)
CHECKPOINT_FILE = Path(__file__).parent.parent / "logs" / "anaf_contact_checkpoint.txt"
LOG_FILE = Path(__file__).parent.parent / "logs" / "refresh_anaf_contact.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)

TODAY = time.strftime("%Y-%m-%d")


def load_checkpoint() -> int:
    """Returnează ultimul offset procesat."""
    if CHECKPOINT_FILE.exists():
        try:
            return int(CHECKPOINT_FILE.read_text().strip())
        except Exception:
            pass
    return 0


def save_checkpoint(offset: int):
    CHECKPOINT_FILE.write_text(str(offset))


def anaf_submit(cuis: list[int]) -> str | None:
    """Trimite batch la ANAF, returnează correlationId."""
    payload = [{"cui": c, "data": TODAY} for c in cuis]
    try:
        req = urllib.request.Request(
            ANAF_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        if data.get("cod") != 200:
            log.warning("ANAF submit non-200: %s", data)
            return None
        return data.get("correlationId")
    except Exception as e:
        log.warning("ANAF submit error: %s", e)
        return None


def anaf_poll(cid: str) -> dict | None:
    """Polls pentru rezultat. Returnează dict cu found/notfound."""
    for attempt in range(MAX_POLL):
        time.sleep(POLL_DELAY * (1 + attempt * 0.5))
        try:
            url = f"{ANAF_URL}?id={cid}"
            with urllib.request.urlopen(url, timeout=20) as r:
                data = json.loads(r.read())
            if data.get("cod") == 200:
                return data
        except Exception as e:
            log.warning("ANAF poll attempt %d error: %s", attempt + 1, e)
    log.warning("ANAF poll timeout for %s", cid)
    return None


def parse_item(item: dict) -> dict | None:
    """Parsează un item ANAF în câmpuri DB."""
    g = item.get("date_generale", {})
    tva_info = item.get("inregistrare_scop_Tva", {})

    cui = g.get("cui")
    if not cui:
        return None

    telefon = g.get("telefon") or None
    if telefon:
        telefon = telefon.strip() or None

    fax = g.get("fax") or None
    if fax:
        fax = fax.strip() or None

    status_efact = bool(g.get("statusRO_e_Factura", False))

    perioade_raw = tva_info.get("perioade_TVA") or []
    perioade = [
        p for p in perioade_raw
        if isinstance(p, dict) and p.get("data_inceput_ScpTVA")
    ]

    return {
        "cui": cui,
        "telefon": telefon,
        "fax": fax,
        "status_ro_efactura": status_efact,
        "tva_perioade": json.dumps(perioade, ensure_ascii=False) if perioade else None,
    }


async def update_batch_db(conn: asyncpg.Connection, records: list[dict]) -> int:
    """Bulk UPDATE în DB pentru lista de records."""
    if not records:
        return 0

    # Folosim executemany pentru eficiență
    await conn.executemany(
        """
        UPDATE companies
        SET
            telefon             = $1,
            fax                 = $2,
            status_ro_efactura  = $3,
            tva_perioade        = $4::jsonb
        WHERE cui = $5
        """,
        [
            (r["telefon"], r["fax"], r["status_ro_efactura"], r["tva_perioade"], r["cui"])
            for r in records
        ],
    )
    return len(records)


async def main():
    log.info("=== refresh_anaf_contact START ===")
    log.info("Target: ALL companies in DB")
    log.info("ANAF URL: %s", ANAF_URL)

    conn = await asyncpg.connect(DSN)

    # Total
    total = await conn.fetchval("SELECT COUNT(*) FROM companies")
    log.info("Total companies: %d", total)

    # Checkpoint
    offset = load_checkpoint()
    if offset > 0:
        log.info("Resuming from offset %d (%.1f%% done)", offset, 100.0 * offset / total)

    processed = offset
    updated = 0
    errors = 0
    batch_num = 0

    try:
        while True:
            # Citim chunk de CUI-uri din DB, ordonate pentru reproducibilitate
            rows = await conn.fetch(
                "SELECT cui FROM companies ORDER BY cui LIMIT $1 OFFSET $2",
                DB_CHUNK, offset
            )
            if not rows:
                break

            cuis_chunk = [r["cui"] for r in rows]
            chunk_updated = 0

            # Procesăm în sub-batch-uri de 500 (limita ANAF)
            for i in range(0, len(cuis_chunk), BATCH_SIZE):
                sub_batch = cuis_chunk[i:i + BATCH_SIZE]
                batch_num += 1

                cid = anaf_submit(sub_batch)
                if not cid:
                    errors += len(sub_batch)
                    time.sleep(RATE_SLEEP)
                    continue

                result = anaf_poll(cid)
                if not result:
                    errors += len(sub_batch)
                    time.sleep(RATE_SLEEP)
                    continue

                records = []
                for item in result.get("found", []):
                    parsed = parse_item(item)
                    if parsed:
                        records.append(parsed)

                n = await update_batch_db(conn, records)
                chunk_updated += n

                # Respectăm rate limit ANAF
                time.sleep(RATE_SLEEP)

            updated += chunk_updated
            offset += len(cuis_chunk)
            processed = offset
            save_checkpoint(offset)

            pct = 100.0 * processed / total
            log.info(
                "Progress: %d/%d (%.1f%%) | updated_this_chunk=%d | total_updated=%d | errors=%d",
                processed, total, pct, chunk_updated, updated, errors,
            )

    except KeyboardInterrupt:
        log.info("Interrupted by user. Checkpoint saved at offset %d", offset)
    except Exception as e:
        log.exception("Fatal error at offset %d: %s", offset, e)
    finally:
        await conn.close()

    log.info("=== DONE === processed=%d updated=%d errors=%d", processed, updated, errors)
    # Ștergem checkpoint la final complet
    if processed >= total and CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        log.info("Checkpoint deleted (run complete)")


if __name__ == "__main__":
    asyncio.run(main())
