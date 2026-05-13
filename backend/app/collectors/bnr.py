"""
BNR (National Bank of Romania) collector — exchange rates.
Hard constraint #8: Only BNR for exchange rates.

v2: Added historic rate fetching, year archive URL.
"""
from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Optional
import xml.etree.ElementTree as ET

from app.collectors.base_connector import BaseConnector
from app.core.logging import get_logger

logger = get_logger(__name__)


class BNRCollector(BaseConnector):
    SOURCE_NAME = "BNR"
    BASE_URL = "https://www.bnr.ro"
    RATE_LIMIT_PER_SECOND = 1.0

    # BNR provides XML feed
    DAILY_RATES_URL = "/nbrfxrates.xml"
    TEN_DAY_RATES_URL = "/nbrfxrates10days.xml"
    # 8.6: Historic — BNR provides yearly XML archives
    YEARLY_ARCHIVE_URL = "/files/xml/years/nbrfxrates{year}.xml"

    async def sync(self, **kwargs) -> dict:
        """Sync latest exchange rates from BNR."""
        processed = 0
        failed = 0

        try:
            response = await self.request("GET", self.DAILY_RATES_URL)
            rates = self._parse_xml(response.text)
            processed = len(rates)
            logger.info("bnr_sync_complete", rates_count=processed)
        except Exception as e:
            logger.error("bnr_sync_failed", error=str(e))
            failed += 1

        return {"processed": processed, "failed": failed, "rates": rates if processed else []}

    async def fetch_single(self, currency: str = "EUR") -> Optional[dict]:
        """Fetch current exchange rate for a currency."""
        try:
            response = await self.request("GET", self.DAILY_RATES_URL)
            rates = self._parse_xml(response.text)

            for rate in rates:
                if rate["moneda"] == currency.upper():
                    return rate
            return None
        except Exception as e:
            logger.error("bnr_fetch_failed", currency=currency, error=str(e))
            return None

    async def fetch_all_rates(self) -> list[dict]:
        """Fetch all current exchange rates."""
        try:
            response = await self.request("GET", self.DAILY_RATES_URL)
            return self._parse_xml(response.text)
        except Exception as e:
            logger.error("bnr_fetch_all_failed", error=str(e))
            return []

    async def fetch_historic_rates(self, year: int) -> list[dict]:
        """8.6: Fetch historic rates for a given year."""
        try:
            url = self.YEARLY_ARCHIVE_URL.format(year=year)
            response = await self.request("GET", url)
            rates = self._parse_xml(response.text)
            logger.info("bnr_historic_fetched", year=year, count=len(rates))
            return rates
        except Exception as e:
            logger.error("bnr_historic_failed", year=year, error=str(e))
            return []

    async def fetch_last_10_days(self) -> list[dict]:
        """Fetch rates for last 10 business days."""
        try:
            response = await self.request("GET", self.TEN_DAY_RATES_URL)
            return self._parse_xml(response.text)
        except Exception as e:
            logger.error("bnr_10day_failed", error=str(e))
            return []

    def _parse_xml(self, xml_text: str) -> list[dict]:
        """Parse BNR XML exchange rate feed."""
        rates = []

        try:
            root = ET.fromstring(xml_text)
            ns = {"bnr": "http://www.bnr.ro/xsd"}

            body = root.find(".//bnr:Body", ns)
            if body is None:
                body = root.find(".//Body")

            if body is None:
                return rates

            for cube in body.findall(".//bnr:Cube", ns) or body.findall(".//Cube"):
                rate_date = cube.get("date")

                for rate in cube.findall("bnr:Rate", ns) or cube.findall("Rate"):
                    currency = rate.get("currency")
                    multiplier = int(rate.get("multiplier", 1))
                    value = Decimal(rate.text) if rate.text else None

                    if currency and value:
                        rates.append({
                            "moneda": currency,
                            "curs": value / multiplier,
                            "multiplicator": multiplier,
                            "data_curs": rate_date,
                            "sursa": "BNR",
                        })

        except ET.ParseError as e:
            logger.error("bnr_xml_parse_error", error=str(e))

        return rates
