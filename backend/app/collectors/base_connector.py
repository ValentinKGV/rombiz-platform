"""
Base connector — abstract class for all data source collectors.
Implements circuit breaker, retry, rate limiting, and logging.
"""
from __future__ import annotations

import abc
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CircuitBreaker:
    """Simple circuit breaker pattern."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open

    def record_failure(self):
        self.failures += 1
        self.last_failure = datetime.now(timezone.utc)
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning("circuit_breaker_opened", failures=self.failures)

    def record_success(self):
        self.failures = 0
        self.state = "closed"

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open" and self.last_failure:
            elapsed = (datetime.now(timezone.utc) - self.last_failure).total_seconds()
            if elapsed > self.reset_timeout:
                self.state = "half-open"
                return True
        return self.state == "half-open"


class BaseConnector(abc.ABC):
    """
    Abstract base class for all data source connectors.
    Provides: HTTP client, circuit breaker, retry logic, rate limiting.
    """

    SOURCE_NAME: str = "unknown"
    BASE_URL: str = ""
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    RATE_LIMIT_PER_SECOND: float = 5.0
    VERIFY_SSL: bool = True

    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self._last_request_time: Optional[float] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={"User-Agent": "RomBiz-Intelligence/1.0"},
                follow_redirects=True,
                verify=self.VERIFY_SSL,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _rate_limit(self):
        """Simple rate limiting."""
        if self._last_request_time is not None:
            elapsed = asyncio.get_event_loop().time() - self._last_request_time
            min_interval = 1.0 / self.RATE_LIMIT_PER_SECOND
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    async def request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """
        Make an HTTP request with circuit breaker, retry, and rate limiting.
        """
        if not self.circuit_breaker.can_execute():
            raise ConnectionError(f"Circuit breaker OPEN for {self.SOURCE_NAME}")

        await self._rate_limit()

        client = await self.get_client()

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await client.request(method, path, **kwargs)
                response.raise_for_status()
                self.circuit_breaker.record_success()
                return response

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited — back off
                    wait = (attempt + 1) * self.RETRY_DELAY * 2
                    logger.warning(
                        "rate_limited",
                        source=self.SOURCE_NAME,
                        wait=wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                elif e.response.status_code >= 500:
                    self.circuit_breaker.record_failure()
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                raise

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ReadError) as e:
                self.circuit_breaker.record_failure()
                logger.error(
                    "request_failed",
                    source=self.SOURCE_NAME,
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    raise

        raise ConnectionError(f"All {self.MAX_RETRIES} attempts failed for {self.SOURCE_NAME}")

    @abc.abstractmethod
    async def sync(self, **kwargs) -> dict:
        """
        Run a sync operation. Returns stats dict.
        Must be implemented by subclasses.
        """
        ...

    @abc.abstractmethod
    async def fetch_single(self, identifier: Any) -> Optional[dict]:
        """
        Fetch data for a single entity.
        Must be implemented by subclasses.
        """
        ...
