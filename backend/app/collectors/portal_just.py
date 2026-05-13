"""
Portal Just collector — court cases via portalquery.just.ro SOAP API.
Căutarea live se face on-demand prin endpoint-ul /dosare/search.
"""
from __future__ import annotations

from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class PortalJustCollector:
    SOURCE_NAME = "PortalJust"

    async def sync(self, **kwargs) -> dict:
        """Sync placeholder — live search se face on-demand via /dosare/search."""
        logger.info("portal_just_sync_skipped", reason="on_demand_only")
        return {"processed": 0, "failed": 0}

    async def fetch_single(self, identifier: str) -> Optional[dict]:
        """Fetch a single case by number (delegates to SOAP)."""
        from app.api.v1.endpoints.dosare import _soap_call
        try:
            results = await _soap_call("CautareDosare", {"numarDosar": identifier})
            return results[0] if results else None
        except Exception as e:
            logger.error("portal_just_fetch_failed", error=str(e))
            return None

    async def fetch_by_company(self, denumire: str) -> list[dict]:
        """Search court cases by company name (delegates to SOAP)."""
        from app.api.v1.endpoints.dosare import _soap_call
        try:
            parts = denumire.strip().split(" ", 1)
            return await _soap_call("CautareDosareParti", {
                "numeParte": parts[0],
                "prenumeParte": parts[1] if len(parts) > 1 else "",
            })
        except Exception as e:
            logger.error("portal_just_company_search_failed", error=str(e))
            return []

    def _parse_case(self, raw: dict) -> Optional[dict]:
        """Backward compat — SOAP parsing handled in dosare endpoint."""
        return raw if raw.get("numar") else None
