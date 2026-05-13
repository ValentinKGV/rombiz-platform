"""
Monitor Oficial (Official Gazette) collector.
Sections: MO4 (commercial/economic), MO7 (court decisions).

The site does NOT expose a public REST API. Data is accessed via:
  - RSS feeds for each section (primary)
  - HTML scraping of search results for per-CUI lookups
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.collectors.base_connector import BaseConnector
from app.core.logging import get_logger

logger = get_logger(__name__)

# Section-level RSS feeds published by monitoruloficial.ro
_SECTION_RSS = {
    "MO4": "https://www.monitoruloficial.ro/rss/mo4.xml",
    "MO7": "https://www.monitoruloficial.ro/rss/mo7.xml",
    # Fallback: the generic feed contains all parts
    "ALL": "https://www.monitoruloficial.ro/rss/",
}


class MonitorOficialCollector(BaseConnector):
    SOURCE_NAME = "MonitorOficial"
    BASE_URL = "https://www.monitoruloficial.ro"
    RATE_LIMIT_PER_SECOND = 0.5
    VERIFY_SSL = False  # monitoruloficial.ro has incomplete cert chain

    async def sync(self, section: str = "MO4", **kwargs) -> dict:
        """
        Sync latest Monitor Oficial entries for a section via RSS.
        Falls back to HTML scraping of the listing page if RSS fails.
        """
        processed = 0
        failed = 0

        try:
            entries = await self._fetch_rss(section)
            if not entries:
                entries = await self._scrape_latest(section)

            for entry in entries:
                try:
                    parsed = self._parse_entry(entry, section)
                    if parsed:
                        processed += 1
                except Exception:
                    failed += 1

        except Exception as e:
            logger.error("mo_sync_failed", section=section, error=str(e))

        return {"processed": processed, "failed": failed, "section": section}

    async def fetch_single(self, cui: int) -> Optional[dict]:
        """
        Fetch Monitor Oficial mentions for a company by scraping the search page.
        """
        try:
            mentions = await self._scrape_search(cui)
            return {"cui": cui, "mentions": mentions} if mentions else None
        except Exception as e:
            logger.error("mo_fetch_failed", cui=cui, error=str(e))
            return None

    # ── Private helpers ─────────────────────────────────────────────────────

    async def _fetch_rss(self, section: str) -> list[dict]:
        """Fetch entries from the RSS feed for a given section."""
        rss_url = _SECTION_RSS.get(section, _SECTION_RSS["ALL"])
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={"User-Agent": "RomBiz-Intelligence/1.0"},
                follow_redirects=True,
                verify=False,
            ) as client:
                resp = await client.get(rss_url)
                resp.raise_for_status()

            import feedparser
            feed = feedparser.parse(resp.text)
            entries = []
            for item in feed.get("entries", []):
                entries.append({
                    "sectiune": section,
                    "tip_act": item.get("title", ""),
                    "data_publicare": item.get("published", "")[:10] if item.get("published") else None,
                    "rezumat": item.get("summary", ""),
                    "url": item.get("link", ""),
                    "cui": self._extract_cui(item.get("title", "") + " " + item.get("summary", "")),
                })
            logger.info("mo_rss_fetched", section=section, count=len(entries))
            return entries

        except Exception as e:
            logger.warning("mo_rss_failed", section=section, rss_url=rss_url, error=str(e))
            return []

    async def _scrape_latest(self, section: str) -> list[dict]:
        """
        Scrape the Monitor Oficial listing page for the latest publications.
        Returns a list of raw entry dicts.
        """
        # Map section codes to the URL path used on the site
        section_paths = {
            "MO4": "/PartIV/",
            "MO7": "/PartVII/",
        }
        path = section_paths.get(section, "/")

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={"User-Agent": "Mozilla/5.0 RomBiz-Intelligence/1.0"},
                follow_redirects=True,
                verify=False,
            ) as client:
                resp = await client.get(f"{self.BASE_URL}{path}")
                resp.raise_for_status()
                html = resp.text

            return self._parse_listing_html(html, section)

        except Exception as e:
            logger.warning("mo_scrape_latest_failed", section=section, error=str(e))
            return []

    async def _scrape_search(self, cui: int) -> list[dict]:
        """
        Scrape the Monitor Oficial search page for a company by CUI.
        """
        search_url = f"{self.BASE_URL}/cauta/?q={cui}"
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={"User-Agent": "Mozilla/5.0 RomBiz-Intelligence/1.0"},
                follow_redirects=True,
                verify=False,
            ) as client:
                resp = await client.get(search_url)
                resp.raise_for_status()
                html = resp.text

            return self._parse_search_html(html, cui)

        except Exception as e:
            logger.warning("mo_scrape_search_failed", cui=cui, error=str(e))
            return []

    def _parse_listing_html(self, html: str, section: str) -> list[dict]:
        """Extract publication entries from the listing page HTML."""
        entries = []
        # Look for article/publication links — adapt selector to site structure
        link_pattern = re.compile(
            r'href="(/(?:PartI[VX]?|PartVI+)/[^"]+)"[^>]*>([^<]{5,120})<',
            re.IGNORECASE,
        )
        date_pattern = re.compile(r"(\d{2}[./]\d{2}[./]\d{4})")
        for match in link_pattern.finditer(html):
            url_path, title = match.group(1), match.group(2).strip()
            date_m = date_pattern.search(title)
            entries.append({
                "sectiune": section,
                "tip_act": title,
                "data_publicare": date_m.group(1) if date_m else None,
                "rezumat": title,
                "url": f"{self.BASE_URL}{url_path}",
                "cui": self._extract_cui(title),
            })
        return entries

    def _parse_search_html(self, html: str, cui: int) -> list[dict]:
        """Extract mentions from the search results HTML."""
        mentions = []
        # Extract result items — the search page returns article titles and links
        item_pattern = re.compile(
            r'<(?:li|div|article)[^>]*class="[^"]*(?:result|item|entry)[^"]*"[^>]*>(.*?)</(?:li|div|article)>',
            re.IGNORECASE | re.DOTALL,
        )
        link_pattern = re.compile(r'href="([^"]+)"[^>]*>([^<]+)<')
        for block in item_pattern.finditer(html):
            block_text = block.group(1)
            lm = link_pattern.search(block_text)
            if lm:
                url, title = lm.group(1), lm.group(2).strip()
                mentions.append(self._parse_entry({
                    "sectiune": None,
                    "tip_act": title,
                    "data_publicare": None,
                    "rezumat": title,
                    "url": url if url.startswith("http") else f"{self.BASE_URL}{url}",
                    "cui": cui,
                }))
        return [m for m in mentions if m]

    @staticmethod
    def _extract_cui(text: str) -> Optional[int]:
        """Try to extract a CUI/CIF from a text string."""
        m = re.search(r"\b(?:CUI|CIF|RO)\s*:?\s*(\d{6,10})\b", text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        return None

    def _parse_entry(self, raw: dict, section: str = None) -> Optional[dict]:
        return {
            "tip_sectiune": section or raw.get("sectiune"),
            "tip_act": raw.get("tip_act"),
            "data_publicare": raw.get("data_publicare"),
            "continut_rezumat": raw.get("rezumat"),
            "url_document": raw.get("url"),
            "cui_asociat": raw.get("cui"),
        }

