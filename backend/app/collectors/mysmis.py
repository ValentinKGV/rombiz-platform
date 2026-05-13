"""
MySMIS / MYSMIS2021 collector — EU-funded projects.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from datetime import datetime, timezone

from app.collectors.base_connector import BaseConnector
from app.core.logging import get_logger

logger = get_logger(__name__)


class MySMISCollector(BaseConnector):
    SOURCE_NAME = "MySMIS"
    BASE_URL = "https://mysmis2021.gov.ro"
    RATE_LIMIT_PER_SECOND = 0.5

    async def sync(self, **kwargs) -> dict:
        """Sync EU-funded project data."""
        processed = 0
        failed = 0

        try:
            response = await self.request("GET", "/api/projects/recent")
            data = response.json()

            for project in data.get("projects", []):
                try:
                    parsed = self._parse_project(project)
                    if parsed:
                        processed += 1
                except Exception:
                    failed += 1

        except Exception as e:
            logger.error("mysmis_sync_failed", error=str(e))

        return {"processed": processed, "failed": failed}

    async def fetch_single(self, cui: int) -> Optional[dict]:
        """Fetch EU projects for a company."""
        try:
            response = await self.request(
                "GET",
                f"/api/projects/search?cui={cui}",
            )
            data = response.json()

            projects = []
            for p in data.get("results", []):
                parsed = self._parse_project(p)
                if parsed:
                    projects.append(parsed)

            return {"cui": cui, "projects": projects} if projects else None

        except Exception as e:
            logger.error("mysmis_fetch_failed", cui=cui, error=str(e))
            return None

    def _parse_project(self, raw: dict) -> Optional[dict]:
        return {
            "titlu": raw.get("title"),
            "program_operational": raw.get("program"),
            "axa_prioritara": raw.get("priority_axis"),
            "valoare_totala_ron": Decimal(str(raw.get("total_value", 0))),
            "finantare_ue_pct": Decimal(str(raw.get("eu_funding_pct", 0))),
            "beneficiar_cui": raw.get("beneficiary_cui"),
            "beneficiar_denumire": raw.get("beneficiary_name"),
            "status": raw.get("status"),
            "data_aprobare": raw.get("approval_date"),
            "data_finalizare": raw.get("end_date"),
        }
