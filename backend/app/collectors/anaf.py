"""
ANAF (National Agency for Fiscal Administration) collector.

Endpoints:
  - Async API: POST https://webservicesp.anaf.ro/AsynchWebService/api/v8/ws/tva
    Submit request, then GET with ?id={correlationId} to retrieve results.
  - Single company API (same pattern)
  - ANAF debts (datorii)

Hard constraint #4: ANAF debts data max 90 days old.
"""
from __future__ import annotations

import asyncio
import httpx
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Optional, Any

from app.collectors.base_connector import BaseConnector
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ANAFCollector(BaseConnector):
    SOURCE_NAME = "ANAF"
    BASE_URL = "https://webservicesp.anaf.ro"
    RATE_LIMIT_PER_SECOND = 1.0  # ANAF is strict about rate limiting
    MAX_RETRIES = 3

    BULK_ENDPOINT = "/AsynchWebService/api/v8/ws/tva"
    MAX_BULK_SIZE = 500  # ANAF limit per request
    POLL_DELAY = 2.0  # seconds to wait before polling for results
    MAX_POLL_ATTEMPTS = 5

    async def _submit_and_poll(self, payload: list[dict]) -> dict:
        """Submit async request to ANAF and poll for results."""
        # Step 1: Submit
        response = await self.request("POST", self.BULK_ENDPOINT, json=payload)
        submit_data = response.json()

        if submit_data.get("cod") != 200:
            raise RuntimeError(f"ANAF submit failed: {submit_data}")

        correlation_id = submit_data.get("correlationId")
        if not correlation_id:
            raise RuntimeError(f"No correlationId in response: {submit_data}")

        # Step 2: Poll for results (fresh client — ANAF closes persistent connections)
        poll_url = f"{self.BASE_URL}{self.BULK_ENDPOINT}"
        for attempt in range(self.MAX_POLL_ATTEMPTS):
            await asyncio.sleep(self.POLL_DELAY * (attempt + 1))
            try:
                async with httpx.AsyncClient(timeout=30.0) as poll_client:
                    poll_resp = await poll_client.get(poll_url, params={"id": correlation_id})
                if poll_resp.status_code == 200:
                    data = poll_resp.json()
                    if data.get("cod") == 200:
                        return data
            except Exception as e:
                logger.warning("anaf_poll_retry", attempt=attempt + 1, error=str(e))

        raise RuntimeError(f"ANAF poll timed out for {correlation_id}")

    async def sync(self, cuis: list[int] = None, **kwargs) -> dict:
        """
        Bulk sync company data from ANAF.
        Processes in batches of 500 CUIs.
        """
        if not cuis:
            return {"status": "no_cuis", "processed": 0}

        total_processed = 0
        total_failed = 0
        results = []

        # Process in batches
        for i in range(0, len(cuis), self.MAX_BULK_SIZE):
            batch = cuis[i:i + self.MAX_BULK_SIZE]
            batch_payload = [
                {"cui": cui, "data": date.today().strftime("%Y-%m-%d")}
                for cui in batch
            ]

            try:
                data = await self._submit_and_poll(batch_payload)

                if "found" in data:
                    for item in data["found"]:
                        parsed = self._parse_company(item)
                        if parsed:
                            results.append(parsed)
                            total_processed += 1
                        else:
                            total_failed += 1

                if "notfound" in data:
                    total_failed += len(data["notfound"])

            except Exception as e:
                logger.error("anaf_batch_failed", batch_start=i, error=str(e))
                total_failed += len(batch)

        logger.info(
            "anaf_sync_complete",
            processed=total_processed,
            failed=total_failed,
        )

        return {
            "status": "completed",
            "processed": total_processed,
            "failed": total_failed,
            "results": results,
        }

    async def fetch_single(self, cui: int) -> Optional[dict]:
        """
        Fetch data for a single company by CUI.
        """
        payload = [{"cui": cui, "data": date.today().strftime("%Y-%m-%d")}]

        try:
            data = await self._submit_and_poll(payload)

            if data.get("found"):
                return self._parse_company(data["found"][0])

            return None

        except Exception as e:
            logger.error("anaf_fetch_failed", cui=cui, error=str(e))
            return None

    async def fetch_debts(self, cui: int) -> Optional[dict]:
        """
        Fetch ANAF debts for a company.
        Hard constraint: data must be max 90 days old.
        """
        try:
            # ANAF debts endpoint (if available via API)
            response = await self.request(
                "GET",
                f"/api/v1/datorii/{cui}",
            )
            data = response.json()

            return {
                "cui": cui,
                "datorii_buget_stat": Decimal(str(data.get("datorii_buget_stat", 0))),
                "datorii_buget_asigurari": Decimal(str(data.get("datorii_buget_asigurari", 0))),
                "datorii_buget_local": Decimal(str(data.get("datorii_buget_local", 0))),
                "data_verificare": date.today(),
                "sursa": "ANAF",
            }
        except Exception as e:
            logger.error("anaf_debts_fetch_failed", cui=cui, error=str(e))
            return None

    def _parse_company(self, raw: dict) -> Optional[dict]:
        """Parse ANAF response into normalized company data."""
        try:
            general = raw.get("date_generale", {})
            tva = raw.get("inregistrare_scop_Tva", {})

            return {
                "cui": general.get("cui"),
                "denumire": general.get("denumire"),
                "adresa": general.get("adresa"),
                "judet": general.get("judet"),
                "localitate": general.get("localitate"),
                "cod_postal": general.get("codPostal"),
                "nr_reg_comert": general.get("nrRegCom"),
                "telefon": general.get("telefon"),
                "stare_firma": general.get("stare_inregistrare"),
                "data_infiintare": general.get("data_infiintare"),

                # TVA
                "tva_activ": tva.get("scpTVA", False),
                "tva_status": "activ" if tva.get("scpTVA") else "inactiv",
                "tva_data_inregistrare": tva.get("dataInregistrareTVA"),
                "tva_data_anulare": tva.get("dataAnulareTVA"),

                # Split TVA
                "tva_la_incasare": raw.get("inregistrare_RTVAI", {}).get("statusTVAIncasare", False),

                # Insolvency
                "insolventa": raw.get("stare_inactiv", {}).get("statusInactiv", False),
                "data_insolventa": raw.get("stare_inactiv", {}).get("dataInactivare"),

                "sursa": "ANAF",
                "data_sync": datetime.now(timezone.utc),
            }
        except Exception as e:
            logger.error("anaf_parse_failed", error=str(e))
            return None

    # ── 8.1: Balance Sheet (Situații Financiare) ──

    async def fetch_balance_sheet(self, cui: int, an_fiscal: int = None) -> Optional[dict]:
        """
        8.1: Fetch balance sheet data from ANAF/MFinanțe.
        Uses the public financial reporting API.
        """
        if an_fiscal is None:
            an_fiscal = date.today().year - 1

        try:
            response = await self.request(
                "GET",
                f"/api/v1/bilant/{cui}",
                params={"an": an_fiscal},
            )
            data = response.json()

            if not data:
                return None

            return {
                "cui": cui,
                "an_fiscal": an_fiscal,
                "cifra_afaceri": Decimal(str(data.get("cifra_afaceri", 0))),
                "profit_net": Decimal(str(data.get("profit_net", 0))),
                "total_active": Decimal(str(data.get("total_active", 0))),
                "active_imobilizate": Decimal(str(data.get("active_imobilizate", 0))),
                "active_circulante": Decimal(str(data.get("active_circulante", 0))),
                "capitaluri_proprii": Decimal(str(data.get("capitaluri_proprii", 0))),
                "datorii_totale": Decimal(str(data.get("datorii", 0))),
                "capital_social": Decimal(str(data.get("capital_social", 0))),
                "nr_angajati": data.get("numar_angajati", 0),
                "sursa": "ANAF",
            }
        except Exception as e:
            logger.error("anaf_balance_sheet_failed", cui=cui, an=an_fiscal, error=str(e))
            return None
