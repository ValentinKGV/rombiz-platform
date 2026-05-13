#!/usr/bin/env python3
"""
Populează tabelul financial_data din company_balance_sheets.

Calculează ratios financiare:
  - rata_lichiditate = active_circulante / datorii_totale (dacă datorii > 0)
  - grad_indatorare  = datorii_totale / total_active (dacă total_active > 0)
  - roa              = profit_net / total_active * 100
  - roe              = profit_net / capitaluri_proprii * 100 (dacă cap_prop > 0)
  - profit_margin    = profit_net / cifra_afaceri * 100 (dacă ca > 0)

Rulează în batches de 50K, cu UPSERT (on conflict do update).
"""
import asyncio
import asyncpg
import logging
import sys

DSN = "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db"
BATCH_SIZE = 50_000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

UPSERT_SQL = """
INSERT INTO financial_data (
    company_id, an_fiscal,
    cifra_afaceri, profit_net, total_active,
    active_imobilizate, active_circulante,
    total_datorii, capitaluri_prop,
    nr_angajati,
    rata_lichiditate, grad_indatorare, roa, roe, profit_margin,
    sursa
)
SELECT
    c.id AS company_id,
    bs.an_fiscal,
    bs.cifra_afaceri,

    -- profit_net: profit minus pierdere; NULL daca nici una disponibila
    CASE
        WHEN bs.profit_net IS NOT NULL OR bs.pierdere_neta IS NOT NULL
        THEN COALESCE(bs.profit_net, 0) - COALESCE(bs.pierdere_neta, 0)
        ELSE NULL
    END                                                             AS profit_net,

    bs.total_active,
    bs.active_imobilizate,
    bs.active_circulante,
    bs.datorii_totale                                               AS total_datorii,
    bs.capitaluri_proprii                                           AS capitaluri_prop,
    NULLIF(bs.nr_salariati, 0)                                      AS nr_angajati,

    -- rata_lichiditate  (cap: 0 .. 9999)
    CASE WHEN bs.datorii_totale > 0 AND bs.active_circulante IS NOT NULL
         THEN LEAST(9999, GREATEST(0,
              ROUND((bs.active_circulante::numeric / bs.datorii_totale), 4)))
         ELSE NULL END,

    -- grad_indatorare  (cap: 0 .. 9999)
    CASE WHEN bs.total_active > 0 AND bs.datorii_totale IS NOT NULL
         THEN LEAST(9999, GREATEST(0,
              ROUND((bs.datorii_totale::numeric / bs.total_active), 4)))
         ELSE NULL END,

    -- roa  (cap: -9999 .. 9999)
    CASE WHEN bs.total_active > 0
             AND (bs.profit_net IS NOT NULL OR bs.pierdere_neta IS NOT NULL)
         THEN LEAST(9999, GREATEST(-9999,
              ROUND(((COALESCE(bs.profit_net, 0) - COALESCE(bs.pierdere_neta, 0))::numeric
                     / bs.total_active * 100), 4)))
         ELSE NULL END,

    -- roe  (cap: -9999 .. 9999)
    CASE WHEN bs.capitaluri_proprii > 0
             AND (bs.profit_net IS NOT NULL OR bs.pierdere_neta IS NOT NULL)
         THEN LEAST(9999, GREATEST(-9999,
              ROUND(((COALESCE(bs.profit_net, 0) - COALESCE(bs.pierdere_neta, 0))::numeric
                     / bs.capitaluri_proprii * 100), 4)))
         ELSE NULL END,

    -- profit_margin  (cap: -9999 .. 9999)
    CASE WHEN bs.cifra_afaceri > 0
             AND (bs.profit_net IS NOT NULL OR bs.pierdere_neta IS NOT NULL)
         THEN LEAST(9999, GREATEST(-9999,
              ROUND(((COALESCE(bs.profit_net, 0) - COALESCE(bs.pierdere_neta, 0))::numeric
                     / bs.cifra_afaceri * 100), 4)))
         ELSE NULL END,

    'MF_BULK'

FROM company_balance_sheets bs
JOIN companies c ON c.cui = bs.cui
WHERE bs.id >= $1 AND bs.id < $2

ON CONFLICT (company_id, an_fiscal) DO UPDATE SET
    cifra_afaceri      = EXCLUDED.cifra_afaceri,
    profit_net         = EXCLUDED.profit_net,
    total_active       = EXCLUDED.total_active,
    active_imobilizate = EXCLUDED.active_imobilizate,
    active_circulante  = EXCLUDED.active_circulante,
    total_datorii      = EXCLUDED.total_datorii,
    capitaluri_prop    = EXCLUDED.capitaluri_prop,
    nr_angajati        = EXCLUDED.nr_angajati,
    rata_lichiditate   = EXCLUDED.rata_lichiditate,
    grad_indatorare    = EXCLUDED.grad_indatorare,
    roa                = EXCLUDED.roa,
    roe                = EXCLUDED.roe,
    profit_margin      = EXCLUDED.profit_margin
"""


async def main() -> None:
    log.info("Connecting...")
    pool = await asyncpg.create_pool(DSN, min_size=2, max_size=4)

    async with pool.acquire() as conn:
        bounds = await conn.fetchrow(
            "SELECT MIN(id) AS mn, MAX(id) AS mx FROM company_balance_sheets"
        )
        id_min, id_max = bounds["mn"], bounds["mx"] + 1
        total_bs = await conn.fetchval("SELECT COUNT(*) FROM company_balance_sheets")
        existing_fd = await conn.fetchval("SELECT COUNT(*) FROM financial_data")

    log.info("Balance sheets: %d | Existing financial_data: %d | ID range: %d-%d",
             total_bs, existing_fd, id_min, id_max - 1)

    inserted_total = 0
    batch_num = 0
    cur = id_min
    while cur < id_max:
        batch_end = min(cur + BATCH_SIZE, id_max)
        async with pool.acquire() as conn:
            result = await conn.execute(UPSERT_SQL, cur, batch_end)
        n = int(result.split()[-1])
        inserted_total += n
        batch_num += 1
        pct = 100.0 * (batch_end - id_min) / (id_max - id_min)
        log.info("Batch %d | bs.id %d-%d | upserted: %d | total: %d | %.1f%%",
                 batch_num, cur, batch_end, n, inserted_total, pct)
        cur = batch_end

    async with pool.acquire() as conn:
        final = await conn.fetchval("SELECT COUNT(*) FROM financial_data")
        years = await conn.fetch(
            "SELECT an_fiscal, COUNT(*) AS cnt FROM financial_data"
            " GROUP BY an_fiscal ORDER BY an_fiscal DESC LIMIT 15"
        )

    log.info("Done. financial_data rows: %d", final)
    log.info("Per year (top 15):")
    for row in years:
        log.info("  %d: %d", row["an_fiscal"], row["cnt"])

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
