#!/usr/bin/env python3
"""
Recalculate data_quality_score for all companies in bulk using SQL.

Formula mirrors app/utils/data_quality.py WEIGHTS:
  identity:     15 pts - CUI, denumire, forma_juridica, j_nr, data_infiintare
  address:      10 pts - adresa_completa, judet, localitate, cod_postal, lat+lng
  fiscal:        8 pts - always (platitor_tva/inactiv_fiscal flags are always present)
  financials:   20 pts - 0=0, 1-2=12, 3+=20
  persons:      10 pts - has at least 1 associated person
  risk_score:    8 pts - has risk score entry
  esg_score:     5 pts - has ESG entry
  data_sources:  8 pts - num data sources: 1+=3.2, 3+=5.6, 5+=8
  enrichment:   10 pts - flags/fields checked (8 boolean checks)
  freshness:     6 pts - updated_at within 7d=6, 30d=4.2, 90d=1.8, else=0

Total: 100 pts
"""
import asyncio
import asyncpg
import logging
import sys

DSN = "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger(__name__)

SCORE_SQL = """
WITH fin_counts AS (
    SELECT company_id, COUNT(*) AS cnt
    FROM financial_data
    GROUP BY company_id
),
person_counts AS (
    SELECT company_id, 1 AS has_person
    FROM company_persons
    GROUP BY company_id
),
risk_flags AS (
    SELECT company_id, 1 AS has_risk
    FROM risk_scores
    GROUP BY company_id
),
esg_flags AS (
    SELECT company_id, 1 AS has_esg
    FROM esg_scores
    GROUP BY company_id
),
contract_flags AS (
    SELECT company_id, 1 AS has_contracts
    FROM public_contracts
    GROUP BY company_id
)
UPDATE companies c
SET data_quality_score = LEAST(100, GREATEST(0, ROUND(

    -- 1. Identity (15 pts): cui, denumire, forma_juridica, j_nr, data_infiintare
    15.0 * (
        (CASE WHEN c.cui IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.denumire IS NOT NULL AND c.denumire != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.forma_juridica IS NOT NULL AND c.forma_juridica != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.j_nr IS NOT NULL AND c.j_nr != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.data_infiintare IS NOT NULL THEN 1 ELSE 0 END)
    ) / 5.0

    -- 2. Address (10 pts): adresa_completa, judet, localitate, cod_postal, geocoded
    + 10.0 * (
        (CASE WHEN c.adresa_completa IS NOT NULL AND c.adresa_completa != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.judet IS NOT NULL AND c.judet != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.localitate IS NOT NULL AND c.localitate != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.cod_postal IS NOT NULL AND c.cod_postal != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.lat IS NOT NULL AND c.lng IS NOT NULL THEN 1 ELSE 0 END)
    ) / 5.0

    -- 3. Fiscal (8 pts): always fully known
    + 8.0

    -- 4. Financial data (20 pts): 0=0, 1-2=12, 3+=20
    + CASE
        WHEN COALESCE(f.cnt, 0) >= 3 THEN 20.0
        WHEN COALESCE(f.cnt, 0) >= 1 THEN 12.0
        ELSE 0.0
      END

    -- 5. Persons (10 pts): at least 1 person
    + CASE WHEN p.has_person = 1 THEN 10.0 ELSE 0.0 END

    -- 6. Risk score (8 pts)
    + CASE WHEN r.has_risk = 1 THEN 8.0 ELSE 0.0 END

    -- 7. ESG score (5 pts)
    + CASE WHEN e.has_esg = 1 THEN 5.0 ELSE 0.0 END

    -- 8. Data sources breadth (8 pts): jsonb key count
    + CASE
        WHEN c.data_sources IS NOT NULL AND c.data_sources NOT IN ('{}','') AND
             (SELECT COUNT(*) FROM jsonb_object_keys(c.data_sources::jsonb)) >= 5 THEN 8.0
        WHEN c.data_sources IS NOT NULL AND c.data_sources NOT IN ('{}','') AND
             (SELECT COUNT(*) FROM jsonb_object_keys(c.data_sources::jsonb)) >= 3 THEN 5.6
        WHEN c.data_sources IS NOT NULL AND c.data_sources NOT IN ('{}','') AND
             (SELECT COUNT(*) FROM jsonb_object_keys(c.data_sources::jsonb)) >= 1 THEN 3.2
        ELSE 0.0
      END

    -- 9. Enrichment checks (10 pts): 8 boolean checks
    + 10.0 * (
        (CASE WHEN c.has_debts IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.has_insolvency IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.has_litigation IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.has_seap_contracts IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.has_eu_projects IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.has_trademarks IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.caen_principal IS NOT NULL AND c.caen_principal != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.capital_social IS NOT NULL THEN 1 ELSE 0 END)
    ) / 8.0

    -- 10. Freshness (6 pts): based on updated_at
    + CASE
        WHEN c.updated_at >= NOW() - INTERVAL '7 days'  THEN 6.0
        WHEN c.updated_at >= NOW() - INTERVAL '30 days' THEN 4.2
        WHEN c.updated_at >= NOW() - INTERVAL '90 days' THEN 1.8
        ELSE 0.0
      END

)::integer)
FROM fin_counts f
LEFT JOIN person_counts p ON p.company_id = c.id
LEFT JOIN risk_flags r ON r.company_id = c.id
LEFT JOIN esg_flags e ON e.company_id = c.id
LEFT JOIN contract_flags cf ON cf.company_id = c.id
WHERE f.company_id = c.id OR f.company_id IS NULL
;
"""


BATCH_SIZE = 200_000
MAX_RETRIES = 5


def build_sql(id_min: int, id_max: int, found: set) -> str:
    # CTEs scoped to the current ID batch — avoids full-table scans.
    # financial_data uses company_id (indexed FK), not cui.
    fin_cte = (
        "SELECT fd.company_id, COUNT(*) AS cnt FROM financial_data fd"
        f" WHERE fd.company_id >= {id_min} AND fd.company_id < {id_max}"
        " GROUP BY fd.company_id"
    ) if "company_balance_sheets" in found else f"SELECT NULL::bigint AS company_id, 0::bigint AS cnt WHERE FALSE"

    person_cte = (
        "SELECT cp.company_id FROM company_persons cp"
        f" WHERE cp.company_id >= {id_min} AND cp.company_id < {id_max}"
        " GROUP BY cp.company_id"
    ) if "company_persons" in found else f"SELECT NULL::bigint AS company_id WHERE FALSE"

    risk_cte = (
        "SELECT rs.company_id FROM risk_scores rs"
        f" WHERE rs.company_id >= {id_min} AND rs.company_id < {id_max}"
    ) if "risk_scores" in found else f"SELECT NULL::bigint AS company_id WHERE FALSE"

    esg_cte = (
        "SELECT es.company_id FROM esg_scores es"
        f" WHERE es.company_id >= {id_min} AND es.company_id < {id_max}"
    ) if "esg_scores" in found else f"SELECT NULL::bigint AS company_id WHERE FALSE"

    return f"""
WITH
all_ids AS (
    SELECT id FROM companies WHERE id >= {id_min} AND id < {id_max}
),
fin_counts AS ({fin_cte}),
person_counts AS ({person_cte}),
risk_flags AS ({risk_cte}),
esg_flags AS ({esg_cte})
UPDATE companies c
SET data_quality_score = LEAST(100, GREATEST(0, ROUND((

    -- 1. Identity (15 pts)
    15.0 * (
        (CASE WHEN c.cui IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.denumire IS NOT NULL AND c.denumire != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.forma_juridica IS NOT NULL AND c.forma_juridica != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.j_nr IS NOT NULL AND c.j_nr != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.data_infiintare IS NOT NULL THEN 1 ELSE 0 END)
    ) / 5.0

    -- 2. Address (10 pts)
    + 10.0 * (
        (CASE WHEN c.adresa_completa IS NOT NULL AND c.adresa_completa != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.judet IS NOT NULL AND c.judet != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.localitate IS NOT NULL AND c.localitate != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.cod_postal IS NOT NULL AND c.cod_postal != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.lat IS NOT NULL AND c.lng IS NOT NULL THEN 1 ELSE 0 END)
    ) / 5.0

    -- 3. Fiscal (8 pts): always fully known
    + 8.0

    -- 4. Financial data (20 pts): via financial_data.company_id (indexed)
    + CASE
        WHEN COALESCE(f.cnt, 0) >= 3 THEN 20.0
        WHEN COALESCE(f.cnt, 0) >= 1 THEN 12.0
        ELSE 0.0
      END

    -- 5. Persons (10 pts)
    + CASE WHEN p.company_id IS NOT NULL THEN 10.0 ELSE 0.0 END

    -- 6. Risk score (8 pts)
    + CASE WHEN r.company_id IS NOT NULL THEN 8.0 ELSE 0.0 END

    -- 7. ESG score (5 pts)
    + CASE WHEN e.company_id IS NOT NULL THEN 5.0 ELSE 0.0 END

    -- 8. Data sources breadth (8 pts)
    + CASE
        WHEN c.data_sources IS NOT NULL
             AND c.data_sources NOT IN ('{{}}', '', 'null')
             AND c.data_sources ~ '^\\{{' THEN
          CASE
            WHEN jsonb_array_length(to_jsonb(array(SELECT jsonb_object_keys(c.data_sources::jsonb)))) >= 5 THEN 8.0
            WHEN jsonb_array_length(to_jsonb(array(SELECT jsonb_object_keys(c.data_sources::jsonb)))) >= 3 THEN 5.6
            WHEN jsonb_array_length(to_jsonb(array(SELECT jsonb_object_keys(c.data_sources::jsonb)))) >= 1 THEN 3.2
            ELSE 0.0
          END
        ELSE 0.0
      END

    -- 9. Enrichment (10 pts): 8 boolean checks
    + 10.0 * (
        (CASE WHEN c.has_debts IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.has_insolvency IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.has_litigation IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.has_seap_contracts IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.has_eu_projects IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.has_trademarks IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN c.caen_principal IS NOT NULL AND c.caen_principal != '' THEN 1 ELSE 0 END) +
        (CASE WHEN c.capital_social IS NOT NULL THEN 1 ELSE 0 END)
    ) / 8.0

    -- 10. Freshness (6 pts)
    + CASE
        WHEN c.updated_at >= NOW() - INTERVAL '7 days'  THEN 6.0
        WHEN c.updated_at >= NOW() - INTERVAL '30 days' THEN 4.2
        WHEN c.updated_at >= NOW() - INTERVAL '90 days' THEN 1.8
        ELSE 0.0
      END

)::integer)))
FROM all_ids
LEFT JOIN fin_counts f ON f.company_id = all_ids.id
LEFT JOIN person_counts p ON p.company_id = all_ids.id
LEFT JOIN risk_flags r ON r.company_id = all_ids.id
LEFT JOIN esg_flags e ON e.company_id = all_ids.id
WHERE c.id = all_ids.id
"""


async def update_batch(pool, id_min: int, id_max: int, found: set) -> int:
    sql = build_sql(id_min, id_max, found)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with pool.acquire() as conn:
                await conn.execute("SET lock_timeout = '0'")
                result = await conn.execute(sql)
                return int(result.split()[-1])
        except asyncpg.exceptions.DeadlockDetectedError:
            log.warning("Batch %d-%d deadlock (attempt %d), retrying in 5s...", id_min, id_max, attempt)
            await asyncio.sleep(5)
        except asyncpg.exceptions.LockNotAvailableError:
            log.warning("Batch %d-%d lock timeout (attempt %d), retrying in 5s...", id_min, id_max, attempt)
            await asyncio.sleep(5)
    log.error("Batch %d-%d failed after %d attempts, skipping", id_min, id_max, MAX_RETRIES)
    return 0


async def main() -> None:
    log.info("Connecting to DB...")
    pool = await asyncpg.create_pool(DSN, min_size=2, max_size=4)

    async with pool.acquire() as conn:
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables WHERE schemaname = 'public'
            AND tablename IN ('risk_scores','esg_scores','company_persons','company_balance_sheets','public_contracts')
            ORDER BY tablename
        """)
        found = {r["tablename"] for r in tables}
        log.info("Found tables: %s", sorted(found))

        bounds = await conn.fetchrow("SELECT MIN(id) AS mn, MAX(id) AS mx FROM companies")
        id_min = bounds["mn"]
        id_max = bounds["mx"] + 1
        total = await conn.fetchval("SELECT COUNT(*) FROM companies")

    log.info("Companies: %d  |  ID range: %d – %d  |  Batch size: %d", total, id_min, id_max - 1, BATCH_SIZE)

    updated_total = 0
    batch_num = 0
    cur = id_min
    while cur < id_max:
        batch_end = min(cur + BATCH_SIZE, id_max)
        n = await update_batch(pool, cur, batch_end, found)
        updated_total += n
        batch_num += 1
        pct = 100.0 * (batch_end - id_min) / (id_max - id_min)
        log.info("Batch %d done: %d updated | total so far: %d | %.1f%%", batch_num, n, updated_total, pct)
        cur = batch_end

    log.info("All batches done. Total updated: %d", updated_total)

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                CASE
                    WHEN data_quality_score < 30 THEN '0-29'
                    WHEN data_quality_score < 50 THEN '30-49'
                    WHEN data_quality_score < 60 THEN '50-59'
                    WHEN data_quality_score < 70 THEN '60-69'
                    WHEN data_quality_score < 80 THEN '70-79'
                    WHEN data_quality_score < 90 THEN '80-89'
                    ELSE '90-100'
                END AS bucket,
                COUNT(*) AS cnt
            FROM companies
            GROUP BY 1 ORDER BY 1
        """)
    log.info("Score distribution:")
    for r in rows:
        log.info("  %s: %d", r["bucket"], r["cnt"])

    await pool.close()
    log.info("DONE")


if __name__ == "__main__":
    asyncio.run(main())
