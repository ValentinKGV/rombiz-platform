"""
BPI (Buletinul Procedurilor de Insolvență) collector.

Fetches insolvency data from BPI.ro via:
  1. RSS feed (daily publications) — primary source
  2. HTML scraping of search results — for per-CUI lookups
  3. REST API fallback (if API access is available)

Persists parsed cases to the insolvency_cases table.
"""
from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy import select   
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base_connector import BaseConnector
from app.core.config import settings
from app.core.logging import get_logger
from app.models.models import Company, InsolvencyCase, DataSourceSyncLog

logger = get_logger(__name__)


class BPICollector(BaseConnector):
    SOURCE_NAME = "BPI"
    BASE_URL = "http://www.bpi.ro"
    RSS_URL = "https://www.buletinul.ro/rss/"
    RATE_LIMIT_PER_SECOND = 1.0
    VERIFY_SSL = False

    async def sync(self, db: AsyncSession = None, **kwargs) -> dict:
        """
        Sync latest insolvency bulletins from BPI RSS feed.
        Persists new cases to the insolvency_cases table.
        """
        stats = {"processed": 0, "inserted": 0, "updated": 0, "failed": 0, "skipped": 0}

        sync_log = None
        if db:
            sync_log = DataSourceSyncLog(
                source_name=self.SOURCE_NAME,
                sync_type="incremental",
                started_at=datetime.now(timezone.utc),
                status="running",
            )
            db.add(sync_log)
            await db.commit()
            await db.refresh(sync_log)

        try:
            # Try RSS feed first (primary source)
            cases = await self._fetch_from_rss()

            if not cases:
                # Fallback to API if configured
                cases = await self._fetch_from_api()

            for case_data in cases:
                stats["processed"] += 1
                try:
                    if db:
                        await self._persist_case(db, case_data)
                        stats["inserted"] += 1
                except Exception as e:
                    stats["failed"] += 1
                    logger.error("bpi_persist_failed", case=case_data.get("nr_dosar_bpi"), error=str(e))

            if db:
                await db.commit()

        except Exception as e:
            stats["error"] = str(e)
            logger.error("bpi_sync_failed", error=str(e))

        if sync_log and db:
            sync_log.completed_at = datetime.now(timezone.utc)
            sync_log.records_processed = stats["processed"]
            sync_log.records_inserted = stats["inserted"]
            sync_log.records_failed = stats["failed"]
            sync_log.status = "completed" if stats["failed"] == 0 else "completed_with_errors"
            sync_log.metadata_json = stats
            await db.commit()

        logger.info("bpi_sync_complete", **stats)
        return stats

    async def fetch_single(self, cui: int, db: AsyncSession = None) -> Optional[dict]:
        """Fetch insolvency cases for a specific company by CUI."""
        try:
            # Try API search
            response = await self.request("GET", f"/api/cases/search?cui={cui}")
            data = response.json()

            cases = []
            for case in data.get("results", []):
                parsed = self._parse_case(case)
                if parsed:
                    cases.append(parsed)
                    if db:
                        await self._persist_case(db, parsed, cui=cui)

            if db and cases:
                await db.commit()

            return {"cui": cui, "cases": cases} if cases else None

        except Exception:
            # Fallback: try RSS-based search
            try:
                return await self._search_via_rss(cui, db)
            except Exception as e:
                logger.error("bpi_fetch_failed", cui=cui, error=str(e))
                return None

    async def _fetch_from_rss(self) -> list[dict]:
        """Parse BPI RSS feed for latest insolvency publications."""
        cases = []
        try:
            response = await self.request("GET", self.RSS_URL, base_url_override=True)
            content = response.text

            import feedparser
            feed = feedparser.parse(content)

            for entry in feed.get("entries", []):
                case = self._parse_rss_entry(entry)
                if case:
                    cases.append(case)

            logger.info("bpi_rss_fetched", entries=len(feed.get("entries", [])), cases_parsed=len(cases))

        except Exception as e:
            logger.warning("bpi_rss_failed", error=str(e))

        return cases

    async def _fetch_from_api(self) -> list[dict]:
        """Fallback: Fetch from BPI REST API if available."""
        cases = []
        try:
            response = await self.request("GET", "/api/bulletins/latest")
            data = response.json()

            for bulletin in data.get("bulletins", []):
                for case in bulletin.get("cases", []):
                    parsed = self._parse_case(case, bulletin.get("date"))
                    if parsed:
                        cases.append(parsed)
        except Exception as e:
            logger.warning("bpi_api_fallback_failed", error=str(e))

        return cases

    async def _search_via_rss(self, cui: int, db: AsyncSession = None) -> Optional[dict]:
        """Search BPI publications for a specific CUI by scanning RSS entries."""
        all_cases = await self._fetch_from_rss()
        matching = [c for c in all_cases if str(c.get("debitor_cui")) == str(cui)]

        if db:
            for case_data in matching:
                await self._persist_case(db, case_data, cui=cui)
            if matching:
                await db.commit()

        return {"cui": cui, "cases": matching} if matching else None

    async def _persist_case(self, db: AsyncSession, case_data: dict, cui: int = None) -> None:
        """Insert or update an insolvency case in the database."""
        target_cui = cui or case_data.get("debitor_cui")
        if not target_cui:
            return

        # Find company
        result = await db.execute(select(Company).where(Company.cui == int(target_cui)))
        company = result.scalar_one_or_none()
        if not company:
            return

        # Check for existing case by dosar number
        nr_dosar = case_data.get("nr_dosar_bpi")
        if nr_dosar:
            existing = await db.execute(
                select(InsolvencyCase).where(
                    InsolvencyCase.company_id == company.id,
                    InsolvencyCase.nr_dosar_bpi == nr_dosar,
                )
            )
            if existing.scalar_one_or_none():
                return  # Already exists

        # Parse dates safely
        def _parse_date(val: Optional[str]) -> Optional[date]:
            if not val:
                return None
            try:
                return datetime.strptime(val[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                return None

        db.add(InsolvencyCase(
            company_id=company.id,
            nr_dosar_bpi=nr_dosar,
            nr_dosar_tribunal=case_data.get("nr_dosar_tribunal"),
            tip_procedura=case_data.get("tip_procedura"),
            tribunal=case_data.get("tribunal"),
            practician=case_data.get("practician"),
            data_publicare=_parse_date(case_data.get("data_publicare")),
            data_deschidere=_parse_date(case_data.get("data_deschidere")),
            status=case_data.get("status", "ACTIV"),
            raw_data=case_data,
        ))
        company.has_insolvency = True

    def _parse_case(self, raw: dict, bulletin_date: str = None) -> Optional[dict]:
        """Parse a raw case dict from the API response."""
        return {
            "nr_dosar_bpi": raw.get("numar_dosar"),
            "tip_procedura": raw.get("tip_procedura"),
            "tribunal": raw.get("tribunal"),
            "practician": raw.get("practician_insolventa"),
            "data_deschidere": raw.get("data_deschidere"),
            "data_publicare": bulletin_date or raw.get("data_publicare"),
            "status": raw.get("status", "activ"),
            "debitor_cui": raw.get("cui_debitor"),
            "debitor_denumire": raw.get("denumire_debitor"),
        }

    def _parse_rss_entry(self, entry: dict) -> Optional[dict]:
        """Extract insolvency case data from an RSS feed entry."""
        title = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))
        published = entry.get("published", "")

        # Try to extract CUI from title/summary
        import re
        cui_match = re.search(r"(?:CUI|RO)\s*:?\s*(\d{6,10})", title + " " + summary)
        dosar_match = re.search(r"(?:dosar|nr\.?)\s*:?\s*([\w/.-]+)", title + " " + summary, re.IGNORECASE)

        # Detect procedure type
        tip_procedura = None
        text_lower = (title + " " + summary).lower()
        if "faliment" in text_lower:
            tip_procedura = "faliment"
        elif "reorganizare" in text_lower:
            tip_procedura = "reorganizare"
        elif "lichidare" in text_lower:
            tip_procedura = "lichidare"
        elif "insolvență" in text_lower or "insolventa" in text_lower:
            tip_procedura = "insolventa"

        return {
            "nr_dosar_bpi": dosar_match.group(1) if dosar_match else None,
            "tip_procedura": tip_procedura,
            "tribunal": None,
            "practician": None,
            "data_deschidere": None,
            "data_publicare": published[:10] if published else None,
            "status": "activ",
            "debitor_cui": int(cui_match.group(1)) if cui_match else None,
            "debitor_denumire": title,
        }
