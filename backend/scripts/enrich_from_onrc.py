#!/usr/bin/env python3
"""
Enrich companies from ONRC od_firme.csv (delimiter: ^)

Fills from CSV (only if DB field is currently empty/null):
  - cod_postal     <- ADR_COD_POSTAL (col 15)
  - j_nr           <- COD_INMATRICULARE (col 2) — fallback, ANAF already filled most
  - adresa_completa <- built from strada + nr + bloc + scara + etaj + ap + sector
  - web            <- WEB (col 18)

CSV columns (0-based after split on ^):
  0  DENUMIRE
  1  CUI
  2  COD_INMATRICULARE
  3  DATA_INMATRICULARE
  4  EUID
  5  FORMA_JURIDICA
  6  ADR_TARA
  7  ADR_JUDET
  8  ADR_LOCALITATE
  9  ADR_DEN_STRADA
 10  ADR_NR_STRADA
 11  ADR_BLOC
 12  ADR_SCARA
 13  ADR_ETAJ
 14  ADR_APARTAMENT
 15  ADR_COD_POSTAL
 16  ADR_SECTOR
 17  ADR_COMPLETARE
 18  WEB
 19  TARA_FIRMA_MAMA
"""
from __future__ import annotations

import asyncio
import asyncpg
import csv
import logging
import os
import sys

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "od_firme.csv")
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "enrich_onrc.log")
DSN = "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db"
BATCH_SIZE = 5000

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def build_adresa(parts: list[str]) -> str | None:
    strada = parts[9].strip()
    nr = parts[10].strip()
    bloc = parts[11].strip()
    scara = parts[12].strip()
    etaj = parts[13].strip()
    ap = parts[14].strip()
    sector = parts[16].strip()
    completare = parts[17].strip()

    tokens = []
    if strada:
        tokens.append(strada)
    if nr:
        tokens.append(f"nr. {nr}")
    if bloc:
        tokens.append(f"bl. {bloc}")
    if scara:
        tokens.append(f"sc. {scara}")
    if etaj:
        tokens.append(f"et. {etaj}")
    if ap:
        tokens.append(f"ap. {ap}")
    if sector:
        tokens.append(f"sector {sector}")
    if completare:
        tokens.append(completare)

    result = ", ".join(tokens).strip(", ")
    return result if result else None


async def upsert_batch(conn: asyncpg.Connection, rows: list[dict]) -> int:
    if not rows:
        return 0

    cuis        = [r["cui"] for r in rows]
    cod_postal  = [r["cod_postal"] for r in rows]
    j_nr        = [r["j_nr"] for r in rows]
    adresa      = [r["adresa"] for r in rows]

    result = await conn.execute(
        """
        UPDATE companies AS c SET
          cod_postal      = COALESCE(NULLIF(c.cod_postal, ''),      v.cod_postal),
          j_nr            = COALESCE(NULLIF(c.j_nr, ''),            v.j_nr),
          adresa_completa = COALESCE(NULLIF(c.adresa_completa, ''), v.adresa)
        FROM (
          SELECT
            unnest($1::int[])  AS cui,
            unnest($2::text[]) AS cod_postal,
            unnest($3::text[]) AS j_nr,
            unnest($4::text[]) AS adresa
        ) AS v
        WHERE c.cui = v.cui
          AND (
            (c.cod_postal IS NULL OR c.cod_postal = '') AND v.cod_postal IS NOT NULL
            OR (c.j_nr IS NULL OR c.j_nr = '') AND v.j_nr IS NOT NULL
            OR (c.adresa_completa IS NULL OR c.adresa_completa = '') AND v.adresa IS NOT NULL
          )
        """,
        cuis, cod_postal, j_nr, adresa,
    )
    return int(result.split()[-1]) if result else 0


async def main() -> None:
    conn = await asyncpg.connect(DSN)

    total_read = 0
    total_updated = 0
    batch: list[dict] = []

    log.info("Opening %s", CSV_PATH)
    with open(CSV_PATH, encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f, delimiter="^")
        next(reader)  # skip header

        for row in reader:
            total_read += 1
            if len(row) < 19:
                continue

            try:
                cui_raw = row[1].strip()
                if not cui_raw or not cui_raw.isdigit():
                    continue
                cui = int(cui_raw)
                if cui <= 0 or cui > 2_147_483_647:  # must fit int4
                    continue
            except ValueError:
                continue

            cod_postal_raw = row[15].strip()
            cod_postal = cod_postal_raw if cod_postal_raw else None

            j_nr_raw = row[2].strip()
            j_nr = j_nr_raw if j_nr_raw else None

            adresa = build_adresa(row)

            # skip rows with nothing useful
            if not any([cod_postal, j_nr, adresa]):
                continue

            batch.append({"cui": cui, "cod_postal": cod_postal, "j_nr": j_nr, "adresa": adresa})

            if len(batch) >= BATCH_SIZE:
                updated = await upsert_batch(conn, batch)
                total_updated += updated
                batch.clear()
                if total_read % 500000 == 0:
                    log.info("Read %d rows | updated %d companies", total_read, total_updated)

    if batch:
        updated = await upsert_batch(conn, batch)
        total_updated += updated

    await conn.close()
    log.info("DONE. Read %d rows | updated %d companies", total_read, total_updated)


if __name__ == "__main__":
    asyncio.run(main())
