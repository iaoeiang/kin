"""Redis caching layer for frequently accessed data."""
from __future__ import annotations

import json
import time
from functools import wraps
from typing import Any, Callable

from agentnet.common.redis_client import get_redis


def cached(ttl: int = 30):
    """Decorator: cache async function results in Redis.

    Usage:
        @cached(ttl=30)
        async def get_expensive_data():
            ...

    Key is auto-derived from function name + args.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            key_parts = ["cache", func.__module__, func.__qualname__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            redis = await get_redis()
            try:
                cached = await redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass  # Redis down — fall through

            result = await func(*args, **kwargs)

            try:
                await redis.setex(cache_key, ttl, json.dumps(result, default=str))
            except Exception:
                pass

            return result
        return wrapper
    return decorator


class StatsCache:
    """In-memory + Redis hybrid stats cache for admin/status."""

    def __init__(self):
        self._cache: dict[str, tuple[float, Any]] = {}
        self._ttl = 30  # seconds

    async def get(self, key: str) -> Any:
        now = time.time()
        if key in self._cache and now - self._cache[key][0] < self._ttl:
            return self._cache[key][1]
        return None

    def set(self, key: str, value: Any):
        self._cache[key] = (time.time(), value)


# Singleton
stats_cache = StatsCache()
