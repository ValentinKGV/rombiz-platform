"""
BVB (Bucharest Stock Exchange) collector.
Fetches listed companies, stock prices, and corporate events.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional, Any

from bs4 import BeautifulSoup
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base_connector import BaseConnector
from app.core.logging import get_logger
from app.models.models import Company, DataSourceSyncLog

logger = get_logger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_float(text: str | None) -> float | None:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.,-]", "", text).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_name(name: str) -> str:
    """Simplify a company name for fuzzy DB matching."""
    name = name.upper().strip()
    for suffix in [" SA", " SRL", " RA", " SNC", " SCS", " RL", " S.A.", " S.R.L."]:
        name = name.removesuffix(suffix)
    return re.sub(r"\s+", " ", name).strip()


class BVBCollector(BaseConnector):
    SOURCE_NAME = "BVB"
    BASE_URL = "https://www.bvb.ro"
    RATE_LIMIT_PER_SECOND = 1.0

    TRADING_DATA_URL = "/FinancialInstruments/Markets/Shares.aspx"
    CORPORATE_EVENTS_URL = "/info/Rapoarte/Corporate/CorporateActions.aspx"
    ISSUER_PROFILE_URL = "/FinancialInstruments/Details/FinancialInstrumentsDetails.aspx"

    async def sync(self, db: AsyncSession | None = None, **kwargs) -> dict:
        """
        Sync BVB listed companies. Fetches trading data and matches companies
        by CUI (from profile page) or by name (fuzzy). Updates company.data_sources
        with BVB stock information.
        """
        stats = {"processed": 0, "matched": 0, "unmatched": 0, "failed": 0}
        sync_log = None

        if db is not None:
            sync_log = DataSourceSyncLog(
                source_name=self.SOURCE_NAME,
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            db.add(sync_log)
            await db.commit()

        try:
            response = await self.request("GET", self.TRADING_DATA_URL)
            instruments = self._parse_trading_page(response.text)
            logger.info("bvb_instruments_fetched", count=len(instruments))

            for instr in instruments:
                try:
                    stats["processed"] += 1
                    if db is None:
                        continue

                    company = await self._find_company(db, instr)
                    if company is None:
                        stats["unmatched"] += 1
                        logger.debug("bvb_company_not_found", ticker=instr.get("isin"), name=instr.get("name"))
                        continue

                    company.data_sources = dict(company.data_sources or {})
                    company.data_sources["bvb"] = {
                        "ticker": instr.get("ticker"),   # short ticker e.g. "TLV"
                        "isin": instr.get("isin"),        # 12-char ISIN e.g. "ROTLVAACNOR1"
                        "market": instr.get("market", "BVB"),
                        "segment": instr.get("segment"),
                        "sector": instr.get("sector"),
                        "last_price": instr.get("last_price"),
                        "change_pct": instr.get("change_pct"),
                        "volume": instr.get("volume"),
                        "market_cap": instr.get("market_cap"),
                        "listed": True,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    stats["matched"] += 1

                except Exception as e:
                    logger.error("bvb_instrument_failed", ticker=instr.get("isin"), error=str(e))
                    stats["failed"] += 1

            if db is not None:
                await db.commit()

        except Exception as e:
            logger.error("bvb_sync_failed", error=str(e))
            stats["failed"] += 1

        if sync_log and db is not None:
            sync_log.status = "completed" if stats["failed"] == 0 else "completed_with_errors"
            sync_log.completed_at = datetime.now(timezone.utc)
            sync_log.records_processed = stats["processed"]
            sync_log.records_failed = stats["failed"]
            sync_log.metadata_json = stats
            await db.commit()

        logger.info("bvb_sync_complete", **stats)
        return stats

    async def _find_company(self, db: AsyncSession, instr: dict) -> Optional[Company]:
        """Try to match a BVB instrument to a Company record."""
        # 1. Try by CUI if available (fetched from profile page)
        cui = instr.get("cui")
        if cui:
            result = await db.execute(select(Company).where(Company.cui == str(cui)))
            company = result.scalar_one_or_none()
            if company:
                return company

        # 2. Fuzzy match by normalized name
        name = instr.get("name", "")
        if not name:
            return None
        norm = _normalize_name(name)
        result = await db.execute(
            select(Company).where(
                func.upper(Company.denumire).contains(norm[:30])
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def fetch_single(self, ticker_or_cui: Any) -> Optional[dict]:
        """Fetch current stock data for a company by ticker symbol."""
        try:
            response = await self.request(
                "GET", self.ISSUER_PROFILE_URL,
                params={"s": str(ticker_or_cui)},
            )
            return self._parse_issuer_profile(response.text)
        except Exception as e:
            logger.error("bvb_fetch_failed", identifier=str(ticker_or_cui), error=str(e))
            return None

    async def fetch_corporate_events(
        self, ticker: str, year: int | None = None
    ) -> list[dict]:
        """Fetch corporate event calendar for a listed company."""
        try:
            params: dict[str, str] = {"s": ticker}
            if year:
                params["year"] = str(year)
            response = await self.request("GET", self.CORPORATE_EVENTS_URL, params=params)
            return self._parse_corporate_events(response.text)
        except Exception as e:
            logger.error("bvb_events_failed", ticker=ticker, error=str(e))
            return []

    # ── HTML Parsers ──────────────────────────────────────────────────────────

    def _parse_trading_page(self, html: str) -> list[dict]:
        """
        Parse BVB Shares page HTML for listed instruments.

        BVB page (https://www.bvb.ro/FinancialInstruments/Markets/Shares.aspx)
        renders a table with id="gv". The "Simbol / ISIN" cell has the structure:
            <td>
              <a href="...?s=TLV"><b>TLV</b></a>
              <p style="...">ROTLVAACNOR1</p>
            </td>
        Columns: 0=Simbol/ISIN  1=Societate  2=Pret(RON)  3=Var.(%)
                 4=Data  5=Categoria
        """
        instruments: list[dict] = []

        SEGMENT_MAP_INTERNAL = {
            "premium": "Premium",
            "standard": "Standard",
            "aero": "AeRO",
            "int'l": "International",
            "international": "International",
        }

        try:
            soup = BeautifulSoup(html, "lxml")
            # BVB main market page uses id="gv"
            table = (
                soup.find("table", id="gv")
                or soup.find("table", id=lambda i: i and "gvBVBSymbols" in i)
                or soup.find("table", class_=lambda c: c and "dataTable" in (c or ""))
            )
            if table is None:
                tables = soup.find_all("table")
                table = max(tables, key=lambda t: len(t.find_all("tr")), default=None)

            if table is None:
                logger.warning("bvb_no_table_found", html_length=len(html))
                return instruments

            rows = table.find_all("tr")
            if not rows:
                return instruments

            for row in rows[1:]:
                cells = row.find_all("td")
                if not cells:
                    continue

                # ── Cell 0: Simbol / ISIN ──
                c0 = cells[0]
                a_tag = c0.find("a")
                p_tag = c0.find("p")
                b_tag = a_tag.find("b") if a_tag else None

                # Ticker from <a><b>TLV</b></a>
                ticker = b_tag.get_text(strip=True) if b_tag else ""
                if not ticker and a_tag:
                    href = a_tag.get("href", "")
                    m = re.search(r"[?&]s=([A-Z0-9]+)", href)
                    ticker = m.group(1) if m else ""

                # ISIN from <p>ROTLVAACNOR1</p>
                isin = p_tag.get_text(strip=True) if p_tag else ""

                if not ticker:
                    continue

                # ── Remaining columns ──
                name = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                price = _to_float(cells[2].get_text(strip=True)) if len(cells) > 2 else None
                change = _to_float(cells[3].get_text(strip=True)) if len(cells) > 3 else None
                seg_raw = cells[5].get_text(strip=True).lower() if len(cells) > 5 else ""
                segment = SEGMENT_MAP_INTERNAL.get(seg_raw, seg_raw.capitalize() if seg_raw else "Standard")

                instruments.append({
                    "ticker": ticker,
                    "name": name,
                    "isin": isin,
                    "last_price": price,
                    "change_pct": change,
                    "volume": None,       # not on main page
                    "market_cap": None,   # not on main page
                    "market": "BVB",
                    "segment": segment,
                    "sector": "",
                })

            logger.info("bvb_trading_parsed", count=len(instruments))
        except Exception as e:
            logger.error("bvb_parse_trading_error", error=str(e))
        return instruments

    def _parse_issuer_profile(self, html: str) -> dict | None:
        """Parse issuer profile page for company details including CUI."""
        try:
            soup = BeautifulSoup(html, "lxml")
            result: dict[str, Any] = {"market": "BVB"}

            # Extract ticker from title or breadcrumb
            title = soup.find("title")
            if title:
                result["ticker"] = title.get_text(strip=True).split(" ")[0]

            # Look for CUI / fiscal code in company info panels
            text = soup.get_text(" ", strip=True)
            cui_match = re.search(r"(?:CUI|C\.U\.I\.|Cod fiscal)[:\s]+(\d{5,10})", text, re.IGNORECASE)
            if cui_match:
                result["cui"] = cui_match.group(1)

            # ISIN
            isin_match = re.search(r"\b(RO[A-Z0-9]{10})\b", text)
            if isin_match:
                result["isin"] = isin_match.group(1)

            # Prices — look for typical BVB quote boxes
            for label_text, key in [
                ("Ultimul pret", "last_price"),
                ("Variatie", "change_pct"),
                ("Capitalizare", "market_cap"),
                ("Volum", "volume"),
                ("P/E", "pe_ratio"),
                ("Dividend", "dividend_yield"),
            ]:
                pattern = re.compile(re.escape(label_text) + r"[^\d-]*([0-9.,%-]+)", re.IGNORECASE)
                m = pattern.search(text)
                if m:
                    result[key] = _to_float(m.group(1))

            return result or None
        except Exception as e:
            logger.error("bvb_profile_parse_error", error=str(e))
            return None

    def _parse_corporate_events(self, html: str) -> list[dict]:
        """Parse corporate events (dividends, AGA, splits) from BVB page."""
        events: list[dict] = []
        try:
            soup = BeautifulSoup(html, "lxml")
            table = soup.find("table", id=lambda i: i and "gv" in (i or ""))
            if table is None:
                tables = soup.find_all("table")
                table = max(tables, key=lambda t: len(t.find_all("tr")), default=None)

            if table is None:
                return events

            rows = table.find_all("tr")
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])] if rows else []

            col = {}
            for i, h in enumerate(headers):
                if "simbol" in h or "symbol" in h:
                    col["ticker"] = i
                elif "tip" in h or "type" in h or "eveniment" in h:
                    col["event_type"] = i
                elif "data" in h or "date" in h or "ex" in h:
                    col["date"] = i
                elif "valoare" in h or "value" in h or "dividend" in h:
                    col["value"] = i
                elif "descriere" in h or "description" in h:
                    col["description"] = i

            for row in rows[1:]:
                cells = row.find_all("td")
                if not cells:
                    continue

                def cell(key: str) -> str:
                    idx = col.get(key)
                    return cells[idx].get_text(strip=True) if idx is not None and idx < len(cells) else ""

                events.append({
                    "ticker": cell("ticker"),
                    "event_type": cell("event_type"),
                    "date": cell("date"),
                    "value": _to_float(cell("value")),
                    "description": cell("description"),
                })
        except Exception as e:
            logger.error("bvb_events_parse_error", error=str(e))
        return events
