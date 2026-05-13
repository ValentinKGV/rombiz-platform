"""
OSIM (State Office for Inventions and Trademarks) collector.
Fetches trademark & patent information and stores to DB.
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base_connector import BaseConnector
from app.core.logging import get_logger
from app.models.models import Company, DataSourceSyncLog, Trademark

logger = get_logger(__name__)


class OSIMCollector(BaseConnector):
    SOURCE_NAME = "OSIM"
    BASE_URL = "https://www.osim.ro"
    RATE_LIMIT_PER_SECOND = 0.5

    async def sync(self, db: AsyncSession = None, batch_size: int = 100, **kwargs) -> dict:
        """
        Full sync — iterate companies and fetch trademark/patent data.
        Logs progress to data_source_sync_log.
        """
        stats = {"processed": 0, "inserted": 0, "updated": 0, "failed": 0, "skipped": 0}

        sync_log = None
        if db:
            sync_log = DataSourceSyncLog(
                source_name=self.SOURCE_NAME,
                sync_type="full",
                started_at=datetime.now(timezone.utc),
                status="running",
            )
            db.add(sync_log)
            await db.commit()
            await db.refresh(sync_log)

        try:
            if not db:
                return {"processed": 0, "failed": 0, "note": "No DB session — skipping sync"}

            # Get companies to sync
            stmt = select(Company.id, Company.denumire).where(Company.stare == "ACTIV").limit(batch_size)
            companies = (await db.execute(stmt)).all()

            for company_id, denumire in companies:
                try:
                    data = await self.fetch_single(denumire or "")
                    stats["processed"] += 1

                    if not data or not data.get("trademarks"):
                        stats["skipped"] += 1
                        continue

                    company = await db.get(Company, company_id)
                    if company:
                        for tm in data["trademarks"]:
                            # Check for duplicate by registration number
                            existing = None
                            if tm.get("nr_inregistrare"):
                                existing_q = await db.execute(
                                    select(Trademark).where(
                                        Trademark.company_id == company_id,
                                        Trademark.nr_inregistrare == tm["nr_inregistrare"],
                                    )
                                )
                                existing = existing_q.scalar_one_or_none()

                            if existing:
                                existing.status = tm.get("status") or existing.status
                                existing.data_expirare = tm.get("data_expirare") or existing.data_expirare
                                stats["updated"] += 1
                            else:
                                db.add(Trademark(
                                    company_id=company_id,
                                    tip=tm.get("tip", "marca"),
                                    denumire=tm.get("denumire"),
                                    nr_inregistrare=tm.get("nr_inregistrare"),
                                    titular=tm.get("titular"),
                                    data_inregistrare=tm.get("data_inregistrare"),
                                    data_expirare=tm.get("data_expirare"),
                                    status=tm.get("status"),
                                    clase_nisa=tm.get("clase_nisa"),
                                    imagine_url=tm.get("imaginea_url"),
                                ))
                                stats["inserted"] += 1

                        company.has_trademarks = True
                        logger.info("osim_trademarks_persisted",
                                    company=denumire,
                                    count=len(data["trademarks"]))

                except Exception as e:
                    stats["failed"] += 1
                    logger.error("osim_sync_company_failed", company=denumire, error=str(e))

            await db.commit()

        except Exception as e:
            stats["error"] = str(e)
            logger.error("osim_sync_failed", error=str(e))

        # Update sync log
        if sync_log and db:
            sync_log.completed_at = datetime.now(timezone.utc)
            sync_log.records_processed = stats["processed"]
            sync_log.records_inserted = stats["inserted"]
            sync_log.records_updated = stats["updated"]
            sync_log.records_failed = stats["failed"]
            sync_log.status = "completed" if stats["failed"] == 0 else "completed_with_errors"
            sync_log.metadata_json = stats
            await db.commit()

        logger.info("osim_sync_complete", **stats)
        return stats

    async def fetch_single(self, identifier: str) -> Optional[dict]:
        """Search trademarks/patents by company name or registration number."""
        if not identifier:
            return None

        try:
            response = await self.request(
                "GET",
                f"/api/trademarks/search?q={identifier}",
            )
            data = response.json()

            marks = []
            for item in data.get("results", []):
                marks.append({
                    "tip": item.get("tip", "marca"),
                    "denumire": item.get("denumire"),
                    "nr_inregistrare": item.get("numar"),
                    "titular": item.get("titular"),
                    "data_inregistrare": item.get("data_inregistrare"),
                    "data_expirare": item.get("data_expirare"),
                    "status": item.get("status"),
                    "clase_nisa": item.get("clase"),
                    "imaginea_url": item.get("image_url"),
                })

            return {"query": identifier, "trademarks": marks}

        except Exception as e:
            logger.error("osim_fetch_failed", query=identifier, error=str(e))
            return None
