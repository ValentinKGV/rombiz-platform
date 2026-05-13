#!/usr/bin/env python3
"""
Populare bulk a bazei de date cu date de la colectorii AEGRM, OSIM, BVB, ASF, INS.

Strategia:
  - AEGRM & OSIM: iterate companii active, fetch_single() per CUI/denumire
  - BVB: un singur sync() care trage toate companiile listate
  - ASF: un singur sync() care trage toate entitățile reglementate
  - INS: un singur sync() care trage indicatorii macroeconomici

Opțiuni:
  --source aegrm|osim|bvb|asf|ins|all   (default: all)
  --batch-size N                          (default: 200 pentru AEGRM/OSIM)
  --limit N                              (max companii de procesat per sursa)
  --offset N                             (skip primele N companii)
  --resume                               (citeste checkpoint si continua de unde s-a oprit)

Exemple:
  python scripts/populate_collectors.py --source bvb
  python scripts/populate_collectors.py --source aegrm --batch-size 100 --resume
  python scripts/populate_collectors.py --source all --limit 50000
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Bootstrap ────────────────────────────────────────────────────────────────
_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
try:
    from dotenv import load_dotenv
    load_dotenv(_backend / ".env", override=False)
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db",
)

CHECKPOINT_DIR = _backend / "logs"
CHECKPOINT_DIR.mkdir(exist_ok=True)


# ── Checkpoint helpers ────────────────────────────────────────────────────────

def _checkpoint_path(source: str) -> Path:
    return CHECKPOINT_DIR / f"populate_{source}.checkpoint.json"


def _load_checkpoint(source: str) -> dict:
    p = _checkpoint_path(source)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"last_id": 0, "processed": 0, "inserted": 0, "failed": 0}


def _save_checkpoint(source: str, state: dict) -> None:
    _checkpoint_path(source).write_text(json.dumps(state, indent=2))


# ── AEGRM populate ────────────────────────────────────────────────────────────

async def populate_aegrm(batch_size: int, limit: int, resume: bool) -> dict:
    """Iterate companii active si fetch garantii AEGRM per CUI."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select, text
    from app.models.models import Company, CompanyDebt
    from app.collectors.aegrm import AEGRMCollector

    state = _load_checkpoint("aegrm") if resume else {"last_id": 0, "processed": 0, "inserted": 0, "failed": 0, "skipped": 0}
    log.info("AEGRM start — last_id=%s processed=%s", state["last_id"], state["processed"])

    engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"), pool_size=5)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    collector = AEGRMCollector()

    total_processed = 0

    try:
        async with Session() as db:
            # Get total count for progress
            result = await db.execute(
                text("SELECT COUNT(*) FROM companies WHERE stare = 'ACTIVA' AND id > :last_id"),
                {"last_id": state["last_id"]}
            )
            remaining = result.scalar()
            log.info("AEGRM: %s companii de procesat", min(remaining, limit) if limit else remaining)

        offset_id = state["last_id"]
        while True:
            if limit and total_processed >= limit:
                break

            async with Session() as db:
                current_batch = min(batch_size, limit - total_processed if limit else batch_size)
                result = await db.execute(
                    select(Company.id, Company.cui, Company.denumire)
                    .where(Company.stare == "ACTIVA")
                    .where(Company.id > offset_id)
                    .order_by(Company.id)
                    .limit(current_batch)
                )
                companies = result.all()

            if not companies:
                break

            for company_id, cui, denumire in companies:
                try:
                    data = await collector.fetch_single(int(cui) if cui else 0)
                    state["processed"] += 1
                    total_processed += 1

                    if not data or not data.get("guarantees"):
                        state.setdefault("skipped", 0)
                        state["skipped"] += 1
                    else:
                        async with Session() as db:
                            for g in data["guarantees"]:
                                existing = await db.execute(
                                    select(CompanyDebt).where(
                                        CompanyDebt.company_id == company_id,
                                        CompanyDebt.sursa == "AEGRM",
                                        CompanyDebt.tip_datorie == g.get("tip_garantie", "garantie_reala"),
                                    )
                                )
                                if not existing.scalar_one_or_none():
                                    db.add(CompanyDebt(
                                        company_id=company_id,
                                        tip_datorie=g.get("tip_garantie", "garantie_reala"),
                                        creditor=g.get("creditor"),
                                        suma=g.get("valoare"),
                                        valuta="RON",
                                        data_inceput=g.get("data_inscriere"),
                                        sursa="AEGRM",
                                        status=g.get("status", "activa"),
                                    ))
                                    state["inserted"] += 1
                            await db.commit()

                except Exception as e:
                    state["failed"] += 1
                    log.warning("AEGRM failed cui=%s: %s", cui, e)

                # Rate limiting — max 5 req/s
                await asyncio.sleep(0.2)

            offset_id = companies[-1][0]
            state["last_id"] = offset_id
            _save_checkpoint("aegrm", state)
            log.info("AEGRM progress: processed=%s inserted=%s failed=%s last_id=%s",
                     state["processed"], state["inserted"], state["failed"], offset_id)

    finally:
        await collector.close()
        await engine.dispose()

    log.info("AEGRM DONE: %s", state)
    return state


# ── OSIM populate ─────────────────────────────────────────────────────────────

async def populate_osim(batch_size: int, limit: int, resume: bool) -> dict:
    """Iterate companii active si fetch marci/brevete OSIM per denumire."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from app.models.models import Company, Trademark
    from app.collectors.osim import OSIMCollector

    state = _load_checkpoint("osim") if resume else {"last_id": 0, "processed": 0, "inserted": 0, "failed": 0, "skipped": 0}
    log.info("OSIM start — last_id=%s processed=%s", state["last_id"], state["processed"])

    engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"), pool_size=5)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    collector = OSIMCollector()

    total_processed = 0
    offset_id = state["last_id"]

    try:
        while True:
            if limit and total_processed >= limit:
                break

            async with Session() as db:
                current_batch = min(batch_size, limit - total_processed if limit else batch_size)
                result = await db.execute(
                    select(Company.id, Company.cui, Company.denumire)
                    .where(Company.stare == "ACTIVA")
                    .where(Company.id > offset_id)
                    .order_by(Company.id)
                    .limit(current_batch)
                )
                companies = result.all()

            if not companies:
                break

            for company_id, cui, denumire in companies:
                try:
                    data = await collector.fetch_single(denumire or "")
                    state["processed"] += 1
                    total_processed += 1

                    if not data or not data.get("trademarks"):
                        state.setdefault("skipped", 0)
                        state["skipped"] += 1
                    else:
                        async with Session() as db:
                            for tm in data["trademarks"]:
                                existing = None
                                if tm.get("nr_inregistrare"):
                                    q = await db.execute(
                                        select(Trademark).where(
                                            Trademark.company_id == company_id,
                                            Trademark.nr_inregistrare == tm["nr_inregistrare"],
                                        )
                                    )
                                    existing = q.scalar_one_or_none()

                                if not existing:
                                    db.add(Trademark(
                                        company_id=company_id,
                                        tip=tm.get("tip", "marca"),
                                        denumire=tm.get("denumire"),
                                        nr_inregistrare=tm.get("nr_inregistrare"),
                                        titular=tm.get("titular"),
                                        data_inregistrare=tm.get("data_inregistrare"),
                                        data_expirare=tm.get("data_expirare"),
                                        status=tm.get("status"),
                                        clase_nisa=tm.get("clase_nisa"),
                                        imagine_url=tm.get("imaginea_url"),
                                    ))
                                    state["inserted"] += 1

                            company_obj = await db.get(Company, company_id)
                            if company_obj:
                                company_obj.has_trademarks = True
                            await db.commit()

                except Exception as e:
                    state["failed"] += 1
                    log.warning("OSIM failed company_id=%s: %s", company_id, e)

                # Rate limiting — OSIM e mai strict
                await asyncio.sleep(0.5)

            offset_id = companies[-1][0]
            state["last_id"] = offset_id
            _save_checkpoint("osim", state)
            log.info("OSIM progress: processed=%s inserted=%s failed=%s last_id=%s",
                     state["processed"], state["inserted"], state["failed"], offset_id)

    finally:
        await collector.close()
        await engine.dispose()

    log.info("OSIM DONE: %s", state)
    return state


# ── BVB populate ──────────────────────────────────────────────────────────────

async def populate_bvb() -> dict:
    """Sync BVB — un singur request care trage toate companiile listate."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.collectors.bvb import BVBCollector

    log.info("BVB sync start")
    engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"), pool_size=3)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    collector = BVBCollector()

    try:
        async with Session() as db:
            stats = await collector.sync(db=db)
    finally:
        await collector.close()
        await engine.dispose()

    log.info("BVB DONE: %s", stats)
    return stats


# ── ASF populate ──────────────────────────────────────────────────────────────

async def populate_asf() -> dict:
    """Sync ASF — entitati reglementate si sanctiuni."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.collectors.asf import ASFCollector

    log.info("ASF sync start")
    engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"), pool_size=3)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    collector = ASFCollector()

    try:
        async with Session() as db:
            stats = await collector.sync(db=db)
    finally:
        await collector.close()
        await engine.dispose()

    log.info("ASF DONE: %s", stats)
    return stats


# ── INS populate ──────────────────────────────────────────────────────────────

async def populate_ins() -> dict:
    """Sync INS — indicatori macroeconomici (PIB, inflatie, somaj, etc.)."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.collectors.ins import INSCollector

    log.info("INS sync start")
    engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"), pool_size=3)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    collector = INSCollector()

    try:
        async with Session() as db:
            stats = await collector.sync(db=db)
    finally:
        await collector.close()
        await engine.dispose()

    log.info("INS DONE: %s", stats)
    return stats


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> None:
    source = args.source
    results = {}

    start = datetime.now(timezone.utc)
    log.info("=" * 60)
    log.info("populate_collectors START — source=%s  %s", source, start.isoformat())
    log.info("=" * 60)

    if source in ("bvb", "all"):
        results["bvb"] = await populate_bvb()

    if source in ("asf", "all"):
        results["asf"] = await populate_asf()

    if source in ("ins", "all"):
        results["ins"] = await populate_ins()

    if source in ("aegrm", "all"):
        results["aegrm"] = await populate_aegrm(
            batch_size=args.batch_size,
            limit=args.limit,
            resume=args.resume,
        )

    if source in ("osim", "all"):
        results["osim"] = await populate_osim(
            batch_size=args.batch_size,
            limit=args.limit,
            resume=args.resume,
        )

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    log.info("=" * 60)
    log.info("populate_collectors DONE în %.0fs", elapsed)
    for src, stats in results.items():
        log.info("  %-8s %s", src.upper(), stats)
    log.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populare bulk date colectori")
    parser.add_argument(
        "--source",
        choices=["aegrm", "osim", "bvb", "asf", "ins", "all"],
        default="all",
        help="Sursa de date de populat (default: all)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        dest="batch_size",
        help="Companii per batch pentru AEGRM/OSIM (default: 200)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Nr maxim de companii de procesat per sursa (0 = nelimitat)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip primele N companii (dupa ID)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Continua de unde s-a oprit (citeste checkpoint)",
    )
    args = parser.parse_args()
    asyncio.run(main(args))
