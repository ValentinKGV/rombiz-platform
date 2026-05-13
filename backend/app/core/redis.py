"""
Redis client singleton for caching, circuit-breakers and rate-limiting.
"""
from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import settings

redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
)


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency — returns the global Redis client."""
    return redis_client
