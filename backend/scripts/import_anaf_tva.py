#!/usr/bin/env python3
"""
Import ANAF TVA status for all companies.

Updates companies table:
  - platitor_tva       ← inregistrare_scop_Tva.scpTVA
  - tva_la_incasare    ← inregistrare_RTVAI.statusTvaIncasare
  - inactiv_fiscal     ← stare_inactiv.statusInactivi
  - split_tva          ← inregistrare_SplitTVA.statusSplitTVA

Also enriches if currently empty:
  - cod_postal         ← date_generale.codPostal
  - j_nr               ← date_generale.nrRegCom  (nr registru comert)

API: POST https://webservicesp.anaf.ro/AsynchWebService/api/v8/ws/tva
     GET  https://webservicesp.anaf.ro/AsynchWebService/api/v8/ws/tva?id={correlationId}

Rate: max 500 CUI/request, ~1 req/sec, 3 concurrent
Checkpoint: backend/logs/anaf_tva_checkpoint.txt  (last processed offset)
"""
from __future__ import annotations

import asyncio
import httpx
import asyncpg
import logging
import os
import sys
import json
from datetime import date, datetime

BATCH_SIZE = 500
CONCURRENCY = 3          # simultaneous inflight requests
POLL_DELAY = 4.0         # seconds to wait before first poll
POLL_RETRY_DELAY = 3.0   # extra seconds between retries
MAX_POLL_ATTEMPTS = 6
SUBMIT_DELAY = 1.1       # seconds between submits (rate limit)

API_BASE = "https://webservicesp.anaf.ro/AsynchWebService/api/v8/ws/tva"
TODAY = date.today().strftime("%Y-%m-%d")

DSN = "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db"

CHECKPOINT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "logs", "anaf_tva_checkpoint.txt"
)
LOG_FILE = os.path.join(
    os.path.dirname(__file__), "..", "logs", "import_anaf_tva.log"
)

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Use stdout only — caller redirects stdout to log file via nohup >> logfile
# Using FileHandler AND redirected stdout would double every line.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def load_checkpoint() -> int:
    try:
        with open(CHECKPOINT_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save_checkpoint(offset: int) -> None:
    with open(CHECKPOINT_FILE, "w") as f:
        f.write(str(offset))


async def submit_batch(client: httpx.AsyncClient, cuis: list[int]) -> str | None:
    payload = [{"cui": c, "data": TODAY} for c in cuis]
    for attempt in range(4):
        try:
            resp = await client.post(API_BASE, json=payload, timeout=30)
            try:
                data = resp.json()
            except Exception:
                body_preview = resp.content[:200]
                log.warning("ANAF submit bad body (status=%d attempt=%d): %r", resp.status_code, attempt + 1, body_preview)
                await asyncio.sleep(2.0 * (attempt + 1))
                continue
            if data.get("cod") == 200:
                cid = data.get("correlationId")
                if cid:
                    return cid
                log.warning("ANAF submit correlationId missing attempt=%d: %s", attempt + 1, data)
                await asyncio.sleep(2.0 * (attempt + 1))
                continue
            log.warning("ANAF submit non-200 attempt=%d: %s", attempt + 1, data)
            await asyncio.sleep(2.0 * (attempt + 1))
        except Exception as e:
            log.warning("ANAF submit exception attempt=%d: %r", attempt + 1, e)
            await asyncio.sleep(2.0 * (attempt + 1))
    return None


async def poll_result(client: httpx.AsyncClient, correlation_id: str) -> dict | None:
    await asyncio.sleep(POLL_DELAY)
    for attempt in range(MAX_POLL_ATTEMPTS):
        try:
            resp = await client.get(
                API_BASE, params={"id": correlation_id},
                timeout=30, follow_redirects=True,
            )
            if resp.status_code == 200 and resp.content:
                try:
                    data = resp.json()
                    if data.get("cod") == 200:
                        return data
                except Exception:
                    pass  # empty / invalid JSON — result not ready yet
        except Exception as e:
            log.warning("poll attempt %d/%d error: %r", attempt + 1, MAX_POLL_ATTEMPTS, str(e))
        await asyncio.sleep(POLL_RETRY_DELAY)
    log.warning("poll timed out for %s", correlation_id)
    return None


def parse_company(item: dict) -> dict:
    dg = item.get("date_generale", {})
    tva = item.get("inregistrare_scop_Tva", {})
    rtvai = item.get("inregistrare_RTVAI", {})
    inactiv = item.get("stare_inactiv", {})
    split = item.get("inregistrare_SplitTVA", {})

    return {
        "cui": dg.get("cui"),
        "platitor_tva": bool(tva.get("scpTVA", False)),
        "tva_la_incasare": bool(rtvai.get("statusTvaIncasare", False)),
        "inactiv_fiscal": bool(inactiv.get("statusInactivi", False)),
        "split_tva": bool(split.get("statusSplitTVA", False)),
        "cod_postal": (dg.get("codPostal") or "").strip() or None,
        "j_nr": (dg.get("nrRegCom") or "").strip() or None,
        "telefon": (dg.get("telefon") or "").strip() or None,
    }


async def upsert_batch(pool: asyncpg.Pool, rows: list[dict]) -> int:
    if not rows:
        return 0

    cuis = [r["cui"] for r in rows]
    platitor = [r["platitor_tva"] for r in rows]
    tva_inc = [r["tva_la_incasare"] for r in rows]
    inactiv = [r["inactiv_fiscal"] for r in rows]
    split = [r["split_tva"] for r in rows]
    cod_postal = [r["cod_postal"] for r in rows]
    j_nr = [r["j_nr"] for r in rows]
    telefon = [r["telefon"] for r in rows]

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE companies AS c SET
              platitor_tva    = v.platitor_tva,
              tva_la_incasare = v.tva_la_incasare,
              inactiv_fiscal  = v.inactiv_fiscal,
              split_tva       = v.split_tva,
              cod_postal      = COALESCE(NULLIF(c.cod_postal, ''), v.cod_postal),
              j_nr            = COALESCE(NULLIF(c.j_nr, ''), v.j_nr),
              telefon         = COALESCE(NULLIF(c.telefon, ''), v.telefon)
            FROM (
              SELECT
                unnest($1::int[])     AS cui,
                unnest($2::bool[])    AS platitor_tva,
                unnest($3::bool[])    AS tva_la_incasare,
                unnest($4::bool[])    AS inactiv_fiscal,
                unnest($5::bool[])    AS split_tva,
                unnest($6::text[])    AS cod_postal,
                unnest($7::text[])    AS j_nr,
                unnest($8::text[])    AS telefon
            ) AS v
            WHERE c.cui = v.cui
            """,
            cuis, platitor, tva_inc, inactiv, split, cod_postal, j_nr, telefon,
        )
    return int(result.split()[-1]) if result else 0


async def worker(
    worker_id: int,
    queue: asyncio.Queue,
    client: httpx.AsyncClient,
    pool: asyncpg.Pool,
    stats: dict,
    rate_lock: asyncio.Lock,
) -> None:
    """Worker coroutine: processes one batch at a time from the queue."""
    while True:
        try:
            batch_idx, batch_cuis = queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        try:
            # Rate limit: only 1 submit per SUBMIT_DELAY seconds globally
            async with rate_lock:
                correlation_id = await submit_batch(client, batch_cuis)
                await asyncio.sleep(SUBMIT_DELAY)

            if not correlation_id:
                stats["failed"] += len(batch_cuis)
                continue

            result = await poll_result(client, correlation_id)
            if not result:
                stats["failed"] += len(batch_cuis)
                continue

            rows = [parse_company(item) for item in result.get("found", [])]
            updated = await upsert_batch(pool, rows)
            notfound = len(result.get("notfound", []))

            stats["processed"] += len(rows)
            stats["updated"] += updated
            stats["notfound"] += notfound
            stats["batches_done"] += 1

        except Exception as e:
            log.error("worker %d batch %d error: %s", worker_id, batch_idx, e)
            stats["failed"] += len(batch_cuis)
        finally:
            queue.task_done()


async def main() -> None:
    start_offset = load_checkpoint()
    log.info("Starting ANAF TVA import from offset=%d", start_offset)

    _init_conn = await asyncpg.connect(DSN)
    try:
        all_cuis: list[int] = [
            r["cui"]
            for r in await _init_conn.fetch("SELECT cui FROM companies ORDER BY cui")
        ]
    finally:
        await _init_conn.close()

    total = len(all_cuis)
    remaining = all_cuis[start_offset:]
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
    log.info(
        "Total CUIs: %d | Already processed: %d | Remaining: %d | Batches: %d",
        total, start_offset, len(remaining), total_batches,
    )

    # Build queue of (batch_idx, cuis)
    queue: asyncio.Queue = asyncio.Queue()
    for i, batch_start in enumerate(range(0, len(remaining), BATCH_SIZE)):
        queue.put_nowait((i, remaining[batch_start : batch_start + BATCH_SIZE]))

    stats = {"processed": 0, "updated": 0, "notfound": 0, "failed": 0, "batches_done": 0}
    rate_lock = asyncio.Lock()

    pool = await asyncpg.create_pool(DSN, min_size=CONCURRENCY, max_size=CONCURRENCY)
    try:
        async with httpx.AsyncClient(
            headers={"Content-Type": "application/json"},
            timeout=30,
            follow_redirects=True,
        ) as client:

            # Spawn CONCURRENCY workers
            workers = [
                asyncio.create_task(
                    worker(i, queue, client, pool, stats, rate_lock)
                )
                for i in range(CONCURRENCY)
            ]

            # Progress reporter
            async def reporter():
                last = 0
                while True:
                    await asyncio.sleep(120)  # log every 2 minutes
                    done = stats["batches_done"]
                    if done != last:
                        last = done
                        offset = start_offset + done * BATCH_SIZE
                        save_checkpoint(offset)
                        pct = 100.0 * done / total_batches if total_batches else 0
                        log.info(
                            "Progress: %d/%d batches (%.1f%%) | processed=%d updated=%d "
                            "notfound=%d failed=%d | checkpoint=%d",
                            done, total_batches, pct,
                            stats["processed"], stats["updated"],
                            stats["notfound"], stats["failed"], offset,
                        )

            reporter_task = asyncio.create_task(reporter())
            await asyncio.gather(*workers)
            reporter_task.cancel()

    finally:
        await pool.close()

    save_checkpoint(start_offset + len(remaining))
    log.info(
        "DONE. batches=%d | processed=%d | updated=%d | notfound=%d | failed=%d",
        stats["batches_done"],
        stats["processed"],
        stats["updated"],
        stats["notfound"],
        stats["failed"],
    )


if __name__ == "__main__":
    asyncio.run(main())
