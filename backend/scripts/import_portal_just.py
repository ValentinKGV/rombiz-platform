#!/usr/bin/env python3
"""
Import court cases from Portal Just (portal.just.ro) for Romanian companies.
Searches by company name as "parte" in litigation.

Target: companies with capital_social IS NOT NULL (more established firms).
Rate limit: max 2 req/sec to be respectful to the government portal.
Results: populates court_cases table, updates has_litigation flag.

Usage:
    python scripts/import_portal_just.py [--limit N] [--min-capital N]

Checkpoint: logs/portal_just.checkpoint.txt  (last processed company_id)
Log:        logs/import_portal_just.log
"""
import asyncio
import asyncpg
import httpx
import re
import logging
import sys
import os
import time
import argparse
from datetime import datetime, date
from urllib.parse import urlencode, urljoin

# ─── Config ────────────────────────────────────────────────────────────────────
DSN          = "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db"
BASE_URL     = "https://portal.just.ro"
DOSARE_URL   = f"{BASE_URL}/SitePages/dosare.aspx"
DELAY_SEC    = 0.6          # delay between requests (≤2 req/sec)
BATCH_SIZE   = 500          # commit every N companies
TIMEOUT_SEC  = 20
LOG_FILE     = "logs/import_portal_just.log"
CKPT_FILE    = "logs/portal_just.checkpoint.txt"

# SharePoint form field names (stable across sessions for this site)
PARTE_FIELD  = "ctl00$PlaceHolderMain$g_4f775c61_3d6d_40df_9a1a_e225bdaab0b2$SPTextSlicerValueTextControl"
EVENTTARGET  = "ctl00$PlaceHolderMain$g_4f775c61_3d6d_40df_9a1a_e225bdaab0b2$SPTextSlicerValueTextControl"

# ─── Logging ───────────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ]
)
log = logging.getLogger(__name__)

# ─── HTML parsing ──────────────────────────────────────────────────────────────

def parse_date(s: str) -> date | None:
    """Parse DD.MM.YYYY date string."""
    s = s.strip()
    try:
        return datetime.strptime(s, "%d.%m.%Y").date()
    except (ValueError, TypeError):
        return None

def parse_results(html: str) -> list[dict]:
    """Parse dosare result rows from SharePoint list view HTML."""
    rows = re.findall(
        r'<tr(?:\s[^>]*)?>(<td class="ms-vb">.*?)</tr>',
        html, re.DOTALL
    )
    results = []
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(cells) < 6:
            continue
        def clean(c):
            return re.sub(r'<[^>]+>', '', c).strip()

        instanta_full = clean(cells[0])
        if not instanta_full:
            continue

        # cell[1]: nr_dosar with link
        nr_dosar_cell = cells[1]
        nr_dosar = clean(nr_dosar_cell)
        link_match = re.search(r'href="([^"]+dosar\.aspx[^"]+)"', nr_dosar_cell)
        dosar_url = None
        if link_match:
            raw = link_match.group(1).replace("&amp;", "&")
            dosar_url = urljoin(BASE_URL + "/", raw.lstrip("./"))

        data_dosar = parse_date(clean(cells[2]))
        obiect = clean(cells[3])[:499] if len(cells) > 3 else None
        materie = clean(cells[4])[:49] if len(cells) > 4 else None
        stadiu = clean(cells[5])[:99] if len(cells) > 5 else None

        # Parse instanta_oras from "Tribunalul CLUJ" → "CLUJ"
        instanta_oras = None
        m = re.match(r'^(?:Tribunalul|Judecătoria|Curtea de Apel)\s+(.+)$', instanta_full)
        if m:
            instanta_oras = m.group(1).strip()

        if nr_dosar:
            results.append({
                "nr_dosar": nr_dosar[:49],
                "instanta": instanta_full[:199],
                "instanta_oras": instanta_oras[:99] if instanta_oras else None,
                "obiect": obiect,
                "materie": materie,
                "stadiu": stadiu,
                "data_dosar": data_dosar,
                "dosar_url": dosar_url,
            })
    return results


def get_viewstate(html: str) -> dict:
    """Extract VIEWSTATE and EVENTVALIDATION from page HTML."""
    def find_val(name):
        m = re.search(
            rf'<input[^>]+name=["\x27]{re.escape(name)}["\x27][^>]+value=["\x27]([^"\x27]*)["\x27]',
            html
        )
        return m.group(1) if m else ""
    return {
        "__VIEWSTATE": find_val("__VIEWSTATE"),
        "__EVENTVALIDATION": find_val("__EVENTVALIDATION"),
        "__REQUESTDIGEST": find_val("__REQUESTDIGEST"),
    }


# ─── HTTP helpers ──────────────────────────────────────────────────────────────

async def fetch_viewstate(client: httpx.AsyncClient) -> dict:
    """GET dosare.aspx to obtain fresh VIEWSTATE."""
    resp = await client.get(DOSARE_URL, timeout=TIMEOUT_SEC)
    resp.raise_for_status()
    tokens = get_viewstate(resp.text)
    log.debug("Got VIEWSTATE len=%d", len(tokens["__VIEWSTATE"]))
    return tokens


async def search_parte(
    client: httpx.AsyncClient,
    tokens: dict,
    name: str
) -> list[dict]:
    """POST search by party name, return list of dosare."""
    postdata = {
        **tokens,
        PARTE_FIELD: name,
        "__EVENTTARGET": EVENTTARGET,
        "__EVENTARGUMENT": "",
    }
    encoded = urlencode(postdata)
    resp = await client.post(
        DOSARE_URL,
        content=encoded.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=TIMEOUT_SEC,
    )
    if resp.status_code != 200:
        log.warning("POST returned HTTP %d for parte=%r", resp.status_code, name)
        return []
    return parse_results(resp.text)


# ─── DB helpers ────────────────────────────────────────────────────────────────

async def insert_cases(conn: asyncpg.Connection, company_id: int, dosare: list[dict]) -> int:
    """Insert court cases, return count inserted."""
    inserted = 0
    for d in dosare:
        try:
            await conn.execute("""
                INSERT INTO court_cases
                    (company_id, nr_dosar, instanta, instanta_oras, obiect,
                     materie, stadiu, data_dosar, source)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'portal_just')
                ON CONFLICT (nr_dosar) DO NOTHING
            """,
                company_id,
                d["nr_dosar"],
                d["instanta"],
                d["instanta_oras"],
                d["obiect"],
                d["materie"],
                d["stadiu"],
                d["data_dosar"],
            )
            inserted += 1
        except Exception as e:
            log.warning("Insert error for dosar %s: %s", d["nr_dosar"], e)
    return inserted


# ─── Main ──────────────────────────────────────────────────────────────────────

async def main(limit: int, min_capital: float) -> None:
    # Load checkpoint
    last_id = 0
    if os.path.exists(CKPT_FILE):
        try:
            last_id = int(open(CKPT_FILE).read().strip())
            log.info("Resuming from company_id > %d", last_id)
        except (ValueError, OSError):
            pass

    log.info("Connecting to DB...")
    pool = await asyncpg.create_pool(DSN, min_size=2, max_size=2)

    async with pool.acquire() as conn:
        # Fetch target companies: those with capital_social set, above min threshold
        # Order by capital_social DESC to process the most important ones first
        companies = await conn.fetch("""
            SELECT id, denumire, cui
            FROM companies
            WHERE id > $1
              AND denumire IS NOT NULL
              AND denumire != ''
              AND capital_social >= $2
            ORDER BY id
            LIMIT $3
        """, last_id, min_capital, limit)

    log.info("Found %d companies to process (capital_social >= %.0f, id > %d)",
             len(companies), min_capital, last_id)

    # Build HTTP client (SSL verification off due to portal.just.ro cert issues)
    transport = httpx.AsyncHTTPTransport(verify=False)
    async with httpx.AsyncClient(transport=transport, follow_redirects=True) as client:

        # Fetch initial VIEWSTATE tokens (reuse for many requests)
        log.info("Fetching initial VIEWSTATE...")
        try:
            tokens = await fetch_viewstate(client)
        except Exception as e:
            log.error("Failed to fetch VIEWSTATE: %s", e)
            return

        # Refresh tokens every 200 requests (session may expire)
        refresh_every = 200

        total_inserted = 0
        total_companies_with_cases = 0
        total_processed = 0

        async with pool.acquire() as conn:
            for idx, company in enumerate(companies):
                company_id = company["id"]
                name = company["denumire"]

                # Refresh VIEWSTATE periodically
                if idx > 0 and idx % refresh_every == 0:
                    try:
                        tokens = await fetch_viewstate(client)
                        log.info("Refreshed VIEWSTATE at idx=%d", idx)
                    except Exception as e:
                        log.warning("VIEWSTATE refresh failed: %s", e)

                # Rate limiting
                await asyncio.sleep(DELAY_SEC)

                # Search Portal Just
                try:
                    dosare = await search_parte(client, tokens, name)
                except Exception as e:
                    log.warning("Search error for %s (id=%d): %s", name[:30], company_id, e)
                    dosare = []

                # Insert results
                if dosare:
                    n = await insert_cases(conn, company_id, dosare)
                    total_inserted += n
                    if n > 0:
                        total_companies_with_cases += 1
                        # Update has_litigation flag
                        await conn.execute(
                            "UPDATE companies SET has_litigation = TRUE WHERE id = $1",
                            company_id
                        )

                total_processed += 1

                # Progress log every 100 companies
                if total_processed % 100 == 0:
                    log.info(
                        "Progress: %d/%d processed | %d cases inserted | %d companies with cases",
                        total_processed, len(companies),
                        total_inserted, total_companies_with_cases
                    )

                # Save checkpoint every BATCH_SIZE
                if total_processed % BATCH_SIZE == 0:
                    with open(CKPT_FILE, "w") as f:
                        f.write(str(company_id))
                    log.info("Checkpoint saved: company_id=%d", company_id)

        # Final checkpoint
        if companies:
            last_processed_id = companies[-1]["id"]
            with open(CKPT_FILE, "w") as f:
                f.write(str(last_processed_id))

    await pool.close()
    log.info(
        "DONE. Processed: %d companies | Cases inserted: %d | Companies with cases: %d",
        total_processed, total_inserted, total_companies_with_cases
    )

    # Final stats + set has_insolvency from faliment cases
    async with asyncpg.connect(DSN) as conn:
        total_cases = await conn.fetchval("SELECT COUNT(*) FROM court_cases")
        companies_litigating = await conn.fetchval(
            "SELECT COUNT(*) FROM companies WHERE has_litigation = TRUE"
        )
        log.info("DB final: court_cases=%d, has_litigation companies=%d",
                 total_cases, companies_litigating)

        # Flag insolvency from faliment court cases
        n_insolvency = await conn.fetchval("""
            WITH upd AS (
                UPDATE companies c
                SET has_insolvency = TRUE
                FROM court_cases cc
                WHERE cc.company_id = c.id
                  AND cc.materie IN ('Faliment', 'Insolventa', 'Insolven\u0163\u0103',
                                     'Insolven\u0163a', 'Insolvabilitate')
                  AND c.has_insolvency IS NOT TRUE
                RETURNING c.id
            ) SELECT COUNT(*) FROM upd
        """)
        log.info("Flagged %d additional companies as has_insolvency from faliment cases", n_insolvency)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50_000,
                        help="Max companies to process (default: 50000)")
    parser.add_argument("--min-capital", type=float, default=10_000.0,
                        help="Min capital_social RON (default: 10000)")
    args = parser.parse_args()

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    asyncio.run(main(limit=args.limit, min_capital=args.min_capital))
