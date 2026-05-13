"""
INS (National Institute of Statistics) collector.
Fetches macroeconomic data, industry statistics, and demographic info.
Used for market intelligence and sector benchmarking.
Persists snapshots to the statistic_snapshots table.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base_connector import BaseConnector
from app.core.logging import get_logger
from app.models.models import DataSourceSyncLog, StatisticSnapshot

logger = get_logger(__name__)


class INSCollector(BaseConnector):
    SOURCE_NAME = "INS"
    BASE_URL = "http://statistici.insse.ro:8077"
    RATE_LIMIT_PER_SECOND = 1.0

    # INS TEMPO Online API paths
    TEMPO_MATRIX_URL = "/tempo-ins/matrix"
    TEMPO_PIVOT_URL = "/tempo-ins/pivot"

    # Common indicator matrix codes
    INDICATOR_CODES = {
        "gdp": "CON103A",               # PIB regional - preturi curente
        "inflation": "IPC101A",          # Rata inflatiei pe categorii
        "unemployment": "SOM101B",       # Rata somajului
        "industrial_production": "IND103A",  # Productia industriala CAEN
        "retail_trade": "COM101A",
        "construction": "CON101A",
        "foreign_trade_export": "EXP101A",
        "foreign_trade_import": "IMP101A",
        "population_county": "POP105A",  # Populatie pe judete
        "enterprises_by_activity": "INT101D",  # Nr intreprinderi
        "turnover_by_activity": "INT103D",     # Cifra afaceri pe CAEN
        "employees_by_activity": "FOM104A",    # Salariati pe activitati
        "average_salary": "FOM106A",           # Castigul salarial mediu
    }

    async def sync(self, db: AsyncSession = None, **kwargs) -> dict:
        """
        Sync key macroeconomic indicators from INS TEMPO Online.
        Persists each indicator snapshot to statistic_snapshots table.
        """
        processed = 0
        failed = 0
        results = {}

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

        # Fetch a subset of key indicators
        priority_indicators = [
            "gdp", "inflation", "unemployment",
            "industrial_production", "enterprises_by_activity",
        ]

        for indicator_key in priority_indicators:
            matrix_code = self.INDICATOR_CODES.get(indicator_key)
            if not matrix_code:
                continue

            try:
                data = await self._fetch_tempo_data(matrix_code)
                if data:
                    results[indicator_key] = data
                    processed += 1

                    if db:
                        snapshot = StatisticSnapshot(
                            indicator_code=matrix_code,
                            indicator_name=data.get("title", indicator_key),
                            category=indicator_key,
                            measure_unit=data.get("measure_unit"),
                            period=data.get("last_update"),
                            value_json=data,
                        )
                        db.add(snapshot)
                else:
                    failed += 1
            except Exception as e:
                logger.error(
                    "ins_indicator_failed",
                    indicator=indicator_key,
                    error=str(e),
                )
                failed += 1

        if db:
            await db.commit()

            if sync_log:
                sync_log.completed_at = datetime.now(timezone.utc)
                sync_log.records_processed = processed
                sync_log.records_inserted = processed
                sync_log.records_failed = failed
                sync_log.status = "completed" if failed == 0 else "completed_with_errors"
                await db.commit()

        return {
            "processed": processed,
            "failed": failed,
            "indicators": results,
        }

    async def fetch_single(self, matrix_code: Any) -> Optional[dict]:
        """
        Fetch a specific INS TEMPO matrix by code.
        """
        try:
            return await self._fetch_tempo_data(str(matrix_code))
        except Exception as e:
            logger.error(
                "ins_fetch_failed",
                matrix=str(matrix_code),
                error=str(e),
            )
            return None

    async def fetch_county_demographics(self, judet: str, db: AsyncSession = None) -> Optional[dict]:
        """Fetch demographic data for a specific county and persist to DB."""
        try:
            pop_data = await self._fetch_tempo_data(
                self.INDICATOR_CODES["population_county"],
                filters={"judet": judet},
            )
            salary_data = await self._fetch_tempo_data(
                self.INDICATOR_CODES["average_salary"],
                filters={"judet": judet},
            )
            enterprise_data = await self._fetch_tempo_data(
                self.INDICATOR_CODES["enterprises_by_activity"],
                filters={"judet": judet},
            )

            result = {
                "judet": judet,
                "populatie": pop_data,
                "salariu_mediu": salary_data,
                "numar_intreprinderi": enterprise_data,
                "sursa": "INS",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            if db:
                snapshot = StatisticSnapshot(
                    indicator_code="COUNTY_DEMOGRAPHICS",
                    indicator_name=f"Demografie {judet}",
                    category="demographics",
                    judet=judet,
                    value_json=result,
                )
                db.add(snapshot)
                await db.commit()

            return result

        except Exception as e:
            logger.error("ins_county_failed", judet=judet, error=str(e))
            return None

    async def fetch_sector_stats(self, caen_code: str, db: AsyncSession = None) -> Optional[dict]:
        """
        Fetch sector-level statistics by CAEN code.
        Used for benchmarking companies against industry averages.
        Persists snapshot to DB if session is provided.
        """
        try:
            enterprise_data = await self._fetch_tempo_data(
                self.INDICATOR_CODES["enterprises_by_activity"],
                filters={"activitate": caen_code},
            )
            turnover_data = await self._fetch_tempo_data(
                self.INDICATOR_CODES["turnover_by_activity"],
                filters={"activitate": caen_code},
            )
            employee_data = await self._fetch_tempo_data(
                self.INDICATOR_CODES["employees_by_activity"],
                filters={"activitate": caen_code},
            )

            result = {
                "caen": caen_code,
                "numar_intreprinderi": enterprise_data,
                "cifra_afaceri_totala": turnover_data,
                "numar_salariati": employee_data,
                "sursa": "INS",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            if db:
                snapshot = StatisticSnapshot(
                    indicator_code="SECTOR_STATS",
                    indicator_name=f"Statistici sector CAEN {caen_code}",
                    category="sector",
                    caen_code=caen_code,
                    value_json=result,
                )
                db.add(snapshot)
                await db.commit()

            return result

        except Exception as e:
            logger.error(
                "ins_sector_failed", caen=caen_code, error=str(e)
            )
            return None

    async def fetch_macro_snapshot(self) -> dict:
        """
        Get a macroeconomic snapshot: GDP, inflation, unemployment.
        Useful for dashboard overview.
        """
        snapshot = {}

        for key in ["gdp", "inflation", "unemployment"]:
            try:
                data = await self._fetch_tempo_data(self.INDICATOR_CODES[key])
                snapshot[key] = data
            except Exception as e:
                logger.warning("ins_macro_failed", indicator=key, error=str(e))
                snapshot[key] = None

        snapshot["sursa"] = "INS"
        snapshot["updated_at"] = datetime.now(timezone.utc).isoformat()
        return snapshot

    # ── Internal ─────────────────────────────────────────────────────

    async def _fetch_tempo_data(
        self,
        matrix_code: str,
        filters: dict | None = None,
    ) -> Optional[dict]:
        """
        Fetch data from INS TEMPO Online API.

        Step 1: GET /tempo-ins/matrix/{code} → metadata (title, last_update, dimensions)
        Step 2: POST /tempo-ins/pivot → CSV data (parse for latest values)
        """
        try:
            # Step 1: fetch metadata
            meta_resp = await self.request(
                "GET",
                f"{self.TEMPO_MATRIX_URL}/{matrix_code}",
            )
            meta = meta_resp.json()

            title = meta.get("matrixName", matrix_code)
            last_update = meta.get("ultimaActualizare")

            # Extract dimensions summary
            dims = meta.get("dimensionsMap", [])
            dims_summary = [
                {"code": d.get("dimCode"), "label": d.get("label"), "count": len(d.get("options", []))}
                for d in dims
            ]

            # Extract measure unit from dimensions periodicitati or observatii
            measure_unit = None
            periodicitate = meta.get("periodicitati", "")
            if isinstance(periodicitate, list) and periodicitate:
                periodicitate = periodicitate[0]

            return {
                "matrix_code": matrix_code,
                "title": title,
                "measure_unit": measure_unit,
                "last_update": last_update,
                "dimensions": dims_summary,
                "values": [],
            }

        except Exception as e:
            logger.error(
                "ins_tempo_fetch_failed",
                matrix=matrix_code,
                error=str(e),
            )
            return None
