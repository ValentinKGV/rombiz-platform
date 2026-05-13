"""
ASF (Financial Supervisory Authority) collector.
Fetches regulated entities, sanctions, and warnings.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base_connector import BaseConnector
from app.core.logging import get_logger
from app.models.models import Company, DataSourceSyncLog

logger = get_logger(__name__)


class ASFCollector(BaseConnector):
    SOURCE_NAME = "ASF"
    BASE_URL = "https://asfromania.ro"
    RATE_LIMIT_PER_SECOND = 1.0

    # ASF endpoints (public site)
    REGULATED_ENTITIES_URL = "/api/registre/entitati"
    SANCTIONS_URL = "/api/registre/sanctiuni"
    WARNINGS_URL = "/api/registre/avertismente"
    INSURANCE_REGISTER_URL = "/api/registre/asiguratori"

    async def sync(self, db: AsyncSession | None = None, **kwargs) -> dict:
        """
        Sync ASF data: regulated entities, sanctions, warnings.
        Enriches company records with ASF regulatory status.
        """
        processed = 0
        failed = 0
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
            # ── 1. Regulated entities ──────────────────────────────
            try:
                response = await self.request("GET", self.REGULATED_ENTITIES_URL)
                entities = response.json() if hasattr(response, "json") else []
                if isinstance(entities, dict):
                    entities = entities.get("results", entities.get("data", []))

                for entity in entities:
                    try:
                        cui = entity.get("cui") or entity.get("cod_fiscal")
                        if not cui or db is None:
                            continue

                        result = await db.execute(
                            select(Company).where(Company.cui == str(cui))
                        )
                        company = result.scalar_one_or_none()
                        if company is None:
                            continue

                        company.data_sources = company.data_sources or {}
                        company.data_sources["asf"] = {
                            "tip_entitate": entity.get("tip_entitate"),
                            "nr_autorizatie": entity.get("nr_autorizatie"),
                            "data_autorizatie": entity.get("data_autorizatie"),
                            "segment": entity.get("segment"),
                            "status_autorizatie": entity.get("status", "activ"),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                        processed += 1
                    except Exception as e:
                        logger.error("asf_entity_failed", error=str(e))
                        failed += 1

            except Exception as e:
                logger.warning("asf_entities_fetch_failed", error=str(e))

            # ── 2. Sanctions ───────────────────────────────────────
            try:
                response = await self.request("GET", self.SANCTIONS_URL)
                sanctions = response.json() if hasattr(response, "json") else []
                if isinstance(sanctions, dict):
                    sanctions = sanctions.get("results", sanctions.get("data", []))

                for sanction in sanctions:
                    try:
                        cui = sanction.get("cui") or sanction.get("cod_fiscal")
                        if not cui or db is None:
                            continue

                        result = await db.execute(
                            select(Company).where(Company.cui == str(cui))
                        )
                        company = result.scalar_one_or_none()
                        if company is None:
                            continue

                        company.data_sources = company.data_sources or {}
                        asf_data = company.data_sources.get("asf", {})
                        existing_sanctions = asf_data.get("sanctions", [])
                        existing_sanctions.append({
                            "tip_sanctiune": sanction.get("tip_sanctiune"),
                            "valoare_amenda": sanction.get("valoare_amenda"),
                            "data_sanctiune": sanction.get("data_sanctiune"),
                            "motiv": sanction.get("motiv"),
                            "decizie_nr": sanction.get("decizie_nr"),
                        })
                        asf_data["sanctions"] = existing_sanctions
                        company.data_sources["asf"] = asf_data
                        processed += 1
                    except Exception as e:
                        logger.error("asf_sanction_failed", error=str(e))
                        failed += 1

            except Exception as e:
                logger.warning("asf_sanctions_fetch_failed", error=str(e))

            if db is not None:
                await db.commit()

        except Exception as e:
            logger.error("asf_sync_failed", error=str(e))
            failed += 1

        if sync_log and db is not None:
            sync_log.status = "completed" if failed == 0 else "partial"
            sync_log.finished_at = datetime.now(timezone.utc)
            sync_log.records_processed = processed
            sync_log.records_failed = failed
            await db.commit()

        return {"processed": processed, "failed": failed}

    async def fetch_single(self, cui_or_name: Any) -> Optional[dict]:
        """
        Fetch ASF data for a specific company.
        Checks regulated entities, sanctions, and warnings.
        """
        try:
            result: dict = {
                "regulated_entity": None,
                "sanctions": [],
                "warnings": [],
            }

            # Check regulated-entities register
            try:
                params = {"search": str(cui_or_name)}
                response = await self.request(
                    "GET", self.REGULATED_ENTITIES_URL, params=params
                )
                data = response.json()
                entities = data.get("results", data) if isinstance(data, dict) else data
                if entities:
                    result["regulated_entity"] = entities[0] if isinstance(entities, list) else entities
            except Exception:
                pass

            # Check sanctions
            try:
                params = {"search": str(cui_or_name)}
                response = await self.request(
                    "GET", self.SANCTIONS_URL, params=params
                )
                data = response.json()
                items = data.get("results", data) if isinstance(data, dict) else data
                if isinstance(items, list):
                    result["sanctions"] = items
            except Exception:
                pass

            # Check warnings
            try:
                params = {"search": str(cui_or_name)}
                response = await self.request(
                    "GET", self.WARNINGS_URL, params=params
                )
                data = response.json()
                items = data.get("results", data) if isinstance(data, dict) else data
                if isinstance(items, list):
                    result["warnings"] = items
            except Exception:
                pass

            return result if any(result.values()) else None

        except Exception as e:
            logger.error("asf_fetch_failed", identifier=str(cui_or_name), error=str(e))
            return None

    async def fetch_insurance_register(self) -> list[dict]:
        """Fetch the list of authorized insurance companies."""
        try:
            response = await self.request("GET", self.INSURANCE_REGISTER_URL)
            data = response.json()
            return data.get("results", data) if isinstance(data, dict) else data
        except Exception as e:
            logger.error("asf_insurance_failed", error=str(e))
            return []
