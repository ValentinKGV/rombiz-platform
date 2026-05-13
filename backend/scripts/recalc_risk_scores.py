#!/usr/bin/env python3
"""
Recalculare bulk risk_scores pentru toate companiile.

Formula (simplificată față de RiskScoringEngine full, dar compatibilă ca rang):

  scor_financiar (0-100):
    - Fără date financiare → 40 (scor neutru)
    - Cu date: Altman Z' simplified:
        Z' = 0.717*X1 + 0.847*X2 + 3.107*X3 + 0.420*X4 + 0.998*X5 (indisponibil fara sales/assets normalizate)
        Simplificat: scor bazat pe profit_margin, grad_indatorare, rata_lichiditate din ultimul an

  scor_legal (0-100):
    - Fără dosare → 80
    - Are insolventa → 0
    - Dosare active / faliment → scor redus

  scor_fiscal (0-100):
    - Fara datorii, platitor TVA activ → 80
    - Cu datorii → penalizare proportionala

  scor_comportamental (0-100):
    - Baza 70
    - Penalizare daca: inactiv_fiscal, split_tva, datorii mari

  TOTAL = 0.30*fin + 0.25*legal + 0.25*fiscal + 0.20*comportamental

  rating: A(80+), B(60-79), C(40-59), D(20-39), E(<20)

Rulare: batches de 100K companii pe ID, UPSERT în risk_scores.
"""
import asyncio
import asyncpg
import logging
import sys
import math

DSN = "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db"
BATCH_SIZE = 100_000
MAX_RETRIES = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def build_upsert_sql(id_min: int, id_max: int) -> str:
    return f"""
WITH latest_fin AS (
    -- Cel mai recent an fiscal per companie
    SELECT DISTINCT ON (company_id)
        company_id,
        an_fiscal,
        COALESCE(rata_lichiditate, 1.0)  AS lichiditate,
        COALESCE(grad_indatorare, 0.5)   AS indatorare,
        COALESCE(roa, 0.0)               AS roa,
        COALESCE(profit_margin, 0.0)     AS profit_margin,
        cifra_afaceri,
        profit_net
    FROM financial_data
    WHERE company_id IN (SELECT id FROM companies WHERE id >= {id_min} AND id < {id_max})
    ORDER BY company_id, an_fiscal DESC
),
fin_years AS (
    -- Numarul de ani de date
    SELECT company_id, COUNT(*) AS n_ani
    FROM financial_data
    WHERE company_id IN (SELECT id FROM companies WHERE id >= {id_min} AND id < {id_max})
    GROUP BY company_id
),
legal_info AS (
    SELECT
        c.id AS company_id,
        COUNT(cc.id)                                              AS n_dosare,
        COUNT(cc.id) FILTER (WHERE cc.materie IN
            ('Faliment','Insolventa','Insolvență','Insolvabilitate'))  AS n_faliment
    FROM companies c
    LEFT JOIN court_cases cc ON cc.company_id = c.id
    WHERE c.id >= {id_min} AND c.id < {id_max}
    GROUP BY c.id
),
debt_info AS (
    SELECT company_id, SUM(suma_restanta) AS total_datorie
    FROM company_debts
    WHERE company_id IN (SELECT id FROM companies WHERE id >= {id_min} AND id < {id_max})
    GROUP BY company_id
),
scores AS (
    SELECT
        c.id AS company_id,

        -- ── SCOR FINANCIAR (0-100) ──────────────────────────────────
        CASE
            WHEN lf.company_id IS NULL THEN 40  -- fara date: neutru
            ELSE LEAST(100, GREATEST(1,
                -- Baza: 50
                -- +lichiditate: max +20 pt la lichidit >= 2, linear
                -- -indatorare: max -20 pt la indatorare >= 1
                -- +profit_margin: max +20 pt la margin >= 10%
                -- +roa: max +10 pt la roa >= 5%
                ROUND(50
                    + LEAST(20, GREATEST(-20, (lf.lichiditate - 1.0) * 15))
                    + LEAST(10,  GREATEST(-20, lf.profit_margin * 1.5))
                    + LEAST(10,  GREATEST(-10, lf.roa * 1.5))
                    - LEAST(20, GREATEST(0, (lf.indatorare - 0.5) * 30))
                    + CASE WHEN fy.n_ani >= 3 THEN 5
                           WHEN fy.n_ani >= 1 THEN 2
                           ELSE 0 END
                )::integer))
        END AS scor_financiar,

        -- ── SCOR LEGAL (0-100) ──────────────────────────────────────
        CASE
            WHEN c.has_insolvency = TRUE                        THEN 5
            WHEN li.n_faliment > 0                              THEN 10
            WHEN li.n_dosare >= 10                              THEN 30
            WHEN li.n_dosare >= 5                               THEN 50
            WHEN li.n_dosare >= 1                               THEN 65
            ELSE                                                     80
        END AS scor_legal,

        -- ── SCOR FISCAL (0-100) ─────────────────────────────────────
        CASE
            WHEN c.inactiv_fiscal = TRUE                        THEN 5
            WHEN di.total_datorie > 1000000                     THEN 15
            WHEN di.total_datorie > 100000                      THEN 35
            WHEN di.total_datorie > 10000                       THEN 55
            WHEN c.has_debts = TRUE                             THEN 60
            WHEN c.platitor_tva = TRUE                          THEN 80
            ELSE                                                     70
        END AS scor_fiscal,

        -- ── SCOR COMPORTAMENTAL (0-100) ─────────────────────────────
        GREATEST(1, 70
            - CASE WHEN c.inactiv_fiscal = TRUE THEN 30 ELSE 0 END
            - CASE WHEN c.split_tva = TRUE THEN 10 ELSE 0 END
            - CASE WHEN c.has_insolvency = TRUE THEN 30 ELSE 0 END
            - CASE WHEN c.has_debts = TRUE THEN 10 ELSE 0 END
            + CASE WHEN c.platitor_tva = TRUE THEN 10 ELSE 0 END
            + CASE WHEN c.capital_social > 50000 THEN 5 ELSE 0 END
        ) AS scor_comportamental,

        -- capital_social pentru limita credit
        c.capital_social

    FROM companies c
    LEFT JOIN latest_fin lf ON lf.company_id = c.id
    LEFT JOIN fin_years fy ON fy.company_id = c.id
    LEFT JOIN legal_info li ON li.company_id = c.id
    LEFT JOIN debt_info di ON di.company_id = c.id
    WHERE c.id >= {id_min} AND c.id < {id_max}
)
INSERT INTO risk_scores (
    company_id, score, rating,
    scor_financiar, scor_legal, scor_fiscal, scor_comportamental,
    limita_credit, probabilitate_insolventa,
    factori_risc, calculat_la, model_versiune
)
SELECT
    company_id,
    -- TOTAL = 0.30*fin + 0.25*legal + 0.25*fiscal + 0.20*comp
    LEAST(100, GREATEST(1,
        ROUND(scor_financiar * 0.30
            + scor_legal * 0.25
            + scor_fiscal * 0.25
            + scor_comportamental * 0.20)::integer
    )) AS score,

    CASE
        WHEN (scor_financiar*0.30 + scor_legal*0.25 + scor_fiscal*0.25 + scor_comportamental*0.20) >= 80 THEN 'A'
        WHEN (scor_financiar*0.30 + scor_legal*0.25 + scor_fiscal*0.25 + scor_comportamental*0.20) >= 60 THEN 'B'
        WHEN (scor_financiar*0.30 + scor_legal*0.25 + scor_fiscal*0.25 + scor_comportamental*0.20) >= 40 THEN 'C'
        WHEN (scor_financiar*0.30 + scor_legal*0.25 + scor_fiscal*0.25 + scor_comportamental*0.20) >= 20 THEN 'D'
        ELSE 'E'
    END AS rating,

    scor_financiar::numeric,
    scor_legal::numeric,
    scor_fiscal::numeric,
    scor_comportamental::numeric,

    -- limita_credit: 10% din capital_social, min 5000, max 10M
    LEAST(10000000, GREATEST(5000,
        COALESCE(capital_social::bigint * 0.10, 5000)::bigint
    )) AS limita_credit,

    -- probabilitate_insolventa: logistica simpla
    ROUND(1.0 / (1.0 + exp(0.1 * (
        (scor_financiar*0.30 + scor_legal*0.25 + scor_fiscal*0.25 + scor_comportamental*0.20) - 30
    )))::numeric, 4) AS probabilitate_insolventa,

    NULL AS factori_risc,
    NOW() AS calculat_la,
    'bulk-2.0' AS model_versiune

FROM scores

ON CONFLICT (company_id) DO UPDATE SET
    score                    = EXCLUDED.score,
    rating                   = EXCLUDED.rating,
    scor_financiar           = EXCLUDED.scor_financiar,
    scor_legal               = EXCLUDED.scor_legal,
    scor_fiscal              = EXCLUDED.scor_fiscal,
    scor_comportamental      = EXCLUDED.scor_comportamental,
    limita_credit            = EXCLUDED.limita_credit,
    probabilitate_insolventa = EXCLUDED.probabilitate_insolventa,
    calculat_la              = EXCLUDED.calculat_la,
    model_versiune           = EXCLUDED.model_versiune
"""


async def run_batch(pool, id_min: int, id_max: int) -> int:
    sql = build_upsert_sql(id_min, id_max)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with pool.acquire() as conn:
                result = await conn.execute(sql)
                return int(result.split()[-1])
        except asyncpg.exceptions.DeadlockDetectedError:
            log.warning("Deadlock batch %d–%d attempt %d, retry in 3s", id_min, id_max, attempt)
            await asyncio.sleep(3)
    log.error("Batch %d–%d failed after %d attempts", id_min, id_max, MAX_RETRIES)
    return 0


async def main() -> None:
    log.info("Connecting...")
    pool = await asyncpg.create_pool(DSN, min_size=2, max_size=4)

    async with pool.acquire() as conn:
        bounds = await conn.fetchrow("SELECT MIN(id) AS mn, MAX(id) AS mx FROM companies")
        id_min, id_max = bounds["mn"], bounds["mx"] + 1
        total = await conn.fetchval("SELECT COUNT(*) FROM companies")
        existing = await conn.fetchval("SELECT COUNT(*) FROM risk_scores")

    log.info("Companies: %d | Existing risk_scores: %d | ID range: %d–%d",
             total, existing, id_min, id_max - 1)

    upserted_total = 0
    batch_num = 0
    cur = id_min
    while cur < id_max:
        batch_end = min(cur + BATCH_SIZE, id_max)
        n = await run_batch(pool, cur, batch_end)
        upserted_total += n
        batch_num += 1
        pct = 100.0 * (batch_end - id_min) / (id_max - id_min)
        log.info("Batch %d | id %d–%d | upserted: %d | total: %d | %.1f%%",
                 batch_num, cur, batch_end, n, upserted_total, pct)
        cur = batch_end

    async with pool.acquire() as conn:
        dist = await conn.fetch("""
            SELECT rating, COUNT(*) AS cnt
            FROM risk_scores GROUP BY rating ORDER BY rating
        """)
        final = await conn.fetchval("SELECT COUNT(*) FROM risk_scores")

    log.info("DONE — risk_scores total: %d", final)
    log.info("Rating distribution:")
    for r in dist:
        log.info("  %s: %d", r["rating"], r["cnt"])

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
