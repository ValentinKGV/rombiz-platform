"""
Monitor Oficial (Official Gazette) collector.
Sections: MO4 (commercial/economic), MO7 (court decisions).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.collectors.base_connector import BaseConnector
from app.core.logging import get_logger

logger = get_logger(__name__)


class MonitorOficialCollector(BaseConnector):
    SOURCE_NAME = "MonitorOficial"
    BASE_URL = "https://www.monitoruloficial.ro"
    RATE_LIMIT_PER_SECOND = 0.5
    VERIFY_SSL = False  # monitoruloficial.ro has incomplete cert chain

    async def sync(self, section: str = "MO4", **kwargs) -> dict:
        """Sync latest Monitor Oficial entries for a section."""
        processed = 0
        failed = 0

        try:
            response = await self.request(
                "GET",
                f"/api/sections/{section}/latest",
            )
            data = response.json()

            for entry in data.get("entries", []):
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
        """Fetch Monitor Oficial mentions for a company."""
        try:
            response = await self.request(
                "GET",
                f"/api/search?cui={cui}",
            )
            data = response.json()

            mentions = []
            for entry in data.get("results", []):
                parsed = self._parse_entry(entry)
                if parsed:
                    mentions.append(parsed)

            return {"cui": cui, "mentions": mentions} if mentions else None

        except Exception as e:
            logger.error("mo_fetch_failed", cui=cui, error=str(e))
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
