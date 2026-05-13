"""
update_bvb_data.py — Fetch fresh BVB market data and update the database.

Fixes:
  - ticker field (was incorrectly stored as ISIN+ticker concatenated)
  - isin field (now properly the 12-char standard ISIN)
  - last_price, change_pct from live BVB page
  - segment correctly identified (Premium / Standard / Int'l)

Usage:
    cd backend && source venv/bin/activate
    python scripts/update_bvb_data.py
"""
from __future__ import annotations

import asyncio
import re
import sys
import os
from datetime import datetime, timezone

import asyncpg
import httpx
from bs4 import BeautifulSoup

DATABASE_URL = "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db"

BVB_SHARES_URL = "https://www.bvb.ro/FinancialInstruments/Markets/Shares.aspx"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Segment normalisation — BVB uses Romanian names on the page
SEGMENT_MAP = {
    "premium": "Premium",
    "standard": "Standard",
    "aero": "AeRO",
    "int'l": "International",
    "international": "International",
}


def _to_float(text: str | None) -> float | None:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.,\-]", "", text).replace(",", ".")
    # handle negative values like "-0,33"
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_bvb_table(html: str) -> list[dict]:
    """
    Parse the BVB Shares.aspx table.

    The 'Simbol / ISIN' cell has the structure:
        <td>
          <a href="...?s=TLV"><b>TLV</b></a>
          <p style="...">ROTLVAACNOR1</p>
        </td>

    Columns (0-based): 0=Simbol/ISIN  1=Societate  2=Pret(RON)  3=Var.(%)
                       4=Data  5=Categoria
    """
    instruments: list[dict] = []
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="gv")
    if table is None:
        print("[WARN] Table #gv not found in BVB response")
        return instruments

    rows = table.find_all("tr")
    print(f"[INFO] BVB table: {len(rows)} rows (including header)")

    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        # --- Ticker and ISIN ---
        c0 = cells[0]
        a_tag = c0.find("a")
        p_tag = c0.find("p")
        b_tag = a_tag.find("b") if a_tag else None

        ticker = b_tag.get_text(strip=True) if b_tag else ""
        isin = p_tag.get_text(strip=True) if p_tag else ""

        if not ticker:
            # fallback: extract ticker from href ?s=TLV
            href = a_tag.get("href", "") if a_tag else ""
            m = re.search(r"[?&]s=([A-Z0-9]+)", href)
            ticker = m.group(1) if m else ""

        if not ticker:
            continue

        # --- Name (col 1) ---
        name = cells[1].get_text(strip=True) if len(cells) > 1 else ""

        # --- Price (col 2) ---
        price = _to_float(cells[2].get_text(strip=True)) if len(cells) > 2 else None

        # --- Change % (col 3) ---
        change = _to_float(cells[3].get_text(strip=True)) if len(cells) > 3 else None

        # --- Segment (col 5) ---
        seg_raw = cells[5].get_text(strip=True).lower() if len(cells) > 5 else ""
        segment = SEGMENT_MAP.get(seg_raw, seg_raw.capitalize() if seg_raw else "Standard")

        instruments.append(
            {
                "ticker": ticker,
                "isin": isin,
                "name": name,
                "last_price": price,
                "change_pct": change,
                "segment": segment,
            }
        )

    print(f"[INFO] Parsed {len(instruments)} instruments from BVB")
    return instruments


def _extract_isin(stored: str) -> tuple[str, str]:
    """
    Extract (ticker, isin) from a stored ISIN value.

    BVB initially stored "TLVROTLVAACNOR1" (ticker + 12-char ISIN concatenated).
    Standard ISIN is always exactly 12 chars (2-letter country code + 10 alphanumeric).
    So: isin = stored[-12:]  and  ticker = stored[:-12]
    """
    stored = stored.upper().strip()
    if len(stored) == 12 and re.match(r"^[A-Z]{2}[A-Z0-9]{10}$", stored):
        # Already a proper ISIN — need to look up the real ticker from instruments
        return "", stored
    if len(stored) > 12:
        isin_candidate = stored[-12:]
        if re.match(r"^[A-Z]{2}[A-Z0-9]{10}$", isin_candidate):
            return stored[:-12], isin_candidate
    return stored, ""


async def update_database(instruments: list[dict]) -> dict[str, int]:
    """Match BVB instruments to companies in DB and update their bvb data."""
    stats = {"matched": 0, "updated": 0, "not_found": 0, "fixed_format": 0}
    now = datetime.now(timezone.utc).isoformat()

    import json

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT id, cui, denumire,
                   data_sources::jsonb->'bvb'->>'isin' AS stored_isin,
                   data_sources::jsonb->'bvb'->>'ticker' AS stored_ticker,
                   data_sources::jsonb AS ds
            FROM companies
            WHERE data_sources::jsonb->'bvb'->>'listed' = 'true'
            """
        )
        print(f"[INFO] Found {len(rows)} BVB-listed companies in DB")

        # Build lookup by proper 12-char ISIN → list of company rows
        # (there may be multiple DB rows that matched the same BVB listing — we update all)
        by_isin: dict[str, list[dict]] = {}
        for r in rows:
            si = (r["stored_isin"] or "").upper()
            _, extracted_isin = _extract_isin(si)
            key = extracted_isin or si
            by_isin.setdefault(key, []).append(dict(r))

        # Index instruments by ISIN for fast lookup
        instr_by_isin: dict[str, dict] = {i["isin"].upper(): i for i in instruments}

        # --- Pass 1: update all companies using fresh BVB data ---
        for instr in instruments:
            isin = instr["isin"].upper()
            ticker = instr["ticker"].upper()

            company_list = (
                by_isin.get(isin)
                or by_isin.get(ticker + isin)
            )

            # Try ends-with fallback
            if not company_list:
                for key, rows_list in by_isin.items():
                    if key.endswith(isin) or isin.endswith(key):
                        company_list = rows_list
                        break

            if not company_list:
                print(f"[WARN] No match for ticker={ticker!r} isin={isin!r}")
                stats["not_found"] += 1
                continue

            stats["matched"] += len(company_list)
            for company in company_list:
                ds = company["ds"]
                if isinstance(ds, str):
                    ds = json.loads(ds)
                bvb = dict(ds.get("bvb", {})) if ds else {}

                bvb["ticker"] = instr["ticker"]
                bvb["isin"] = instr["isin"]
                bvb["last_price"] = instr["last_price"]
                bvb["change_pct"] = instr["change_pct"]
                bvb["segment"] = instr["segment"]
                bvb["listed"] = True
                bvb["updated_at"] = now

                ds_new = dict(ds or {})
                ds_new["bvb"] = bvb

                await conn.execute(
                    "UPDATE companies SET data_sources = $1::jsonb WHERE id = $2",
                    json.dumps(ds_new),
                    company["id"],
                )
                stats["updated"] += 1

            print(
                f"  ✓ {instr['ticker']:<6} {instr['isin']:<14}  "
                f"price={instr['last_price']}  chg={instr['change_pct']}%  "
                f"seg={instr['segment']}  (matched {len(company_list)} row(s))"
            )

        # --- Pass 2: fix any remaining old-format ISIN entries not matched above ---
        # These are companies that had an old-format ISIN that somehow didn't match
        remaining = await conn.fetch(
            """
            SELECT id, data_sources::jsonb AS ds,
                   data_sources::jsonb->'bvb'->>'isin' AS stored_isin
            FROM companies
            WHERE data_sources::jsonb->'bvb'->>'listed' = 'true'
              AND data_sources::jsonb->'bvb'->>'isin' NOT SIMILAR TO '[A-Z]{2}[A-Z0-9]{10}'
            """
        )
        print(f"\n[INFO] Pass 2: {len(remaining)} entries still with non-standard ISIN")
        for row in remaining:
            si = row["stored_isin"] or ""
            ticker_part, isin_part = _extract_isin(si)
            if not isin_part:
                continue

            ds = row["ds"]
            if isinstance(ds, str):
                ds = json.loads(ds)
            bvb = dict(ds.get("bvb", {})) if ds else {}

            # Use fresh price data if available
            fresh = instr_by_isin.get(isin_part)
            bvb["isin"] = isin_part
            bvb["ticker"] = fresh["ticker"] if fresh else ticker_part
            if fresh:
                bvb["last_price"] = fresh["last_price"]
                bvb["change_pct"] = fresh["change_pct"]
                bvb["segment"] = fresh["segment"]
            bvb["updated_at"] = now

            ds_new = dict(ds or {})
            ds_new["bvb"] = bvb

            await conn.execute(
                "UPDATE companies SET data_sources = $1::jsonb WHERE id = $2",
                json.dumps(ds_new),
                row["id"],
            )
            stats["fixed_format"] += 1
            print(f"  ~ fixed format: {ticker_part!r} → ticker={bvb['ticker']!r} isin={isin_part!r}")

    finally:
        await conn.close()

    return stats


async def main() -> None:
    print("=" * 60)
    print("BVB Data Updater")
    print("=" * 60)

    print(f"\n[1/3] Fetching BVB market data from {BVB_SHARES_URL} ...")
    async with httpx.AsyncClient(
        headers=HEADERS, timeout=30, follow_redirects=True
    ) as client:
        resp = await client.get(BVB_SHARES_URL)
        resp.raise_for_status()
        print(f"      HTTP {resp.status_code}, {len(resp.text)} chars")

    print("\n[2/3] Parsing instruments ...")
    instruments = parse_bvb_table(resp.text)

    if not instruments:
        print("[ERROR] No instruments parsed — aborting")
        sys.exit(1)

    print(f"\n[3/3] Updating database ...")
    stats = await update_database(instruments)

    print("\n" + "=" * 60)
    print(
        f"Done! matched={stats['matched']}  updated={stats['updated']}  "
        f"fixed_format={stats['fixed_format']}  not_found={stats['not_found']}"
    )
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
