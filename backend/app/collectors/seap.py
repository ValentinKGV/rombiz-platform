"""
SEAP (Electronic System for Public Procurement) collector.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from datetime import datetime, timezone

from app.collectors.base_connector import BaseConnector
from app.core.logging import get_logger

logger = get_logger(__name__)


class SEAPCollector(BaseConnector):
    SOURCE_NAME = "SEAP"
    BASE_URL = "https://e-licitatie.ro"
    RATE_LIMIT_PER_SECOND = 1.0
    VERIFY_SSL = False  # e-licitatie.ro has SSL handshake issues

    async def sync(self, **kwargs) -> dict:
        """Sync latest tenders and awarded contracts."""
        processed = 0
        failed = 0

        # Sync active tenders
        try:
            response = await self.request("GET", "/api/tenders/active")
            data = response.json()

            for tender in data.get("tenders", []):
                try:
                    parsed = self._parse_tender(tender)
                    if parsed:
                        processed += 1
                except Exception:
                    failed += 1
        except Exception as e:
            logger.error("seap_tenders_sync_failed", error=str(e))

        # Sync awarded contracts
        try:
            response = await self.request("GET", "/api/contracts/recent")
            data = response.json()

            for contract in data.get("contracts", []):
                try:
                    parsed = self._parse_contract(contract)
                    if parsed:
                        processed += 1
                except Exception:
                    failed += 1
        except Exception as e:
            logger.error("seap_contracts_sync_failed", error=str(e))

        return {"processed": processed, "failed": failed}

    async def fetch_single(self, identifier: int) -> Optional[dict]:
        """Fetch a specific tender or contract."""
        try:
            response = await self.request("GET", f"/api/tenders/{identifier}")
            return response.json()
        except Exception as e:
            logger.error("seap_fetch_failed", id=identifier, error=str(e))
            return None

    def _parse_tender(self, raw: dict) -> Optional[dict]:
        return {
            "titlu": raw.get("title"),
            "autoritate_contractanta": raw.get("authority"),
            "cod_cpv": raw.get("cpv_code"),
            "valoare_estimata_ron": Decimal(str(raw.get("estimated_value", 0))),
            "tip_procedura": raw.get("procedure_type"),
            "data_publicare": raw.get("published_date"),
            "data_limita_depunere": raw.get("submission_deadline"),
            "url_seap": raw.get("url"),
        }

    def _parse_contract(self, raw: dict) -> Optional[dict]:
        return {
            "nr_contract": raw.get("contract_number"),
            "autoritate_contractanta": raw.get("authority"),
            "furnizor_cui": raw.get("supplier_cui"),
            "furnizor_denumire": raw.get("supplier_name"),
            "titlu_contract": raw.get("title"),
            "valoare_ron": Decimal(str(raw.get("value_ron", 0))),
            "valoare_eur": Decimal(str(raw.get("value_eur", 0))) if raw.get("value_eur") else None,
            "data_atribuire": raw.get("award_date"),
            "cod_cpv": raw.get("cpv_code"),
        }
