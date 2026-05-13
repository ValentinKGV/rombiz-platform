"""
AEGRM (Arhiva Electronică de Garanții Reale Mobiliare) collector.
Fetches guarantee/mortgage records and stores to DB.
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base_connector import BaseConnector
from app.core.logging import get_logger
from app.models.models import Company, CompanyDebt, DataSourceSyncLog

logger = get_logger(__name__)


class AEGRMCollector(BaseConnector):
    SOURCE_NAME = "AEGRM"
    BASE_URL = "https://www.aegrm.ro"
    RATE_LIMIT_PER_SECOND = 0.5

    async def sync(self, db: AsyncSession = None, batch_size: int = 100, **kwargs) -> dict:
        """
        Full sync — iterate companies and fetch guarantee records.
        Logs progress to data_source_sync_log.
        """
        stats = {"processed": 0, "inserted": 0, "updated": 0, "failed": 0, "skipped": 0}

        # Create sync log entry
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
            stmt = select(Company.id, Company.cui).where(Company.stare == "ACTIV").limit(batch_size)
            companies = (await db.execute(stmt)).all()

            for company_id, cui in companies:
                try:
                    data = await self.fetch_single(int(cui) if cui else 0)
                    stats["processed"] += 1

                    if not data or not data.get("guarantees"):
                        stats["skipped"] += 1
                        continue

                    for g in data["guarantees"]:
                        # Check if already exists
                        existing = await db.execute(
                            select(CompanyDebt).where(
                                CompanyDebt.company_id == company_id,
                                CompanyDebt.sursa == "AEGRM",
                                CompanyDebt.tip_datorie == g.get("tip_garantie", "garantie_reala"),
                            )
                        )
                        if existing.scalar_one_or_none():
                            stats["updated"] += 1
                            continue

                        debt = CompanyDebt(
                            company_id=company_id,
                            tip_datorie=g.get("tip_garantie", "garantie_reala"),
                            creditor=g.get("creditor"),
                            suma=g.get("valoare"),
                            valuta="RON",
                            data_inceput=g.get("data_inscriere"),
                            sursa="AEGRM",
                            status=g.get("status", "activa"),
                        )
                        db.add(debt)
                        stats["inserted"] += 1

                except Exception as e:
                    stats["failed"] += 1
                    logger.error("aegrm_sync_company_failed", cui=cui, error=str(e))

            await db.commit()

        except Exception as e:
            stats["error"] = str(e)
            logger.error("aegrm_sync_failed", error=str(e))

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

        logger.info("aegrm_sync_complete", **stats)
        return stats

    async def fetch_single(self, cui: int) -> Optional[dict]:
        """Fetch mortgage/guarantee records for a company by CUI."""
        if not cui:
            return None

        try:
            response = await self.request(
                "GET",
                f"/api/search?cui={cui}",
            )
            data = response.json()

            guarantees = []
            for item in data.get("results", []):
                guarantees.append({
                    "tip_garantie": item.get("tip", "garantie_reala"),
                    "creditor": item.get("creditor"),
                    "valoare": item.get("valoare"),
                    "data_inscriere": item.get("data_inscriere"),
                    "status": item.get("status", "activa"),
                    "numar_inscriere": item.get("numar"),
                    "descriere": item.get("descriere"),
                })

            return {"cui": cui, "guarantees": guarantees} if guarantees else None

        except Exception as e:
            logger.error("aegrm_fetch_failed", cui=cui, error=str(e))
            return None
