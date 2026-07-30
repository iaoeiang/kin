"""Rate limiting middleware. Uses sliding window per credential prefix."""
from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


class RateLimiter:
    """Simple in-memory sliding window rate limiter.

    Default: 60 requests per minute per credential prefix.
    Override by prefix in config.
    """

    def __init__(self, default_rpm: int = 60, window: int = 60):
        self.default_rpm = default_rpm
        self.window = window
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_rpm: int | None = None) -> bool:
        now = time.monotonic()
        cutoff = now - self.window
        bucket = self._buckets[key]
        # Prune
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        limit = max_rpm or self.default_rpm
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True

    def remaining(self, key: str, max_rpm: int | None = None) -> int:
        now = time.monotonic()
        cutoff = now - self.window
        bucket = self._buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        limit = max_rpm or self.default_rpm
        return max(0, limit - len(bucket))


rate_limiter = RateLimiter()


def add_rate_limiting(app: FastAPI):
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next: Callable[[Request], Any]):
        # Only rate-limit API routes
        path = request.url.path
        if not path.startswith(("/api/", "/v1/")):
            return await call_next(request)

        # Extract credential prefix from Authorization header
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            prefix = token[:16] if token else "unknown"
        else:
            prefix = f"ip:{request.client.host}" if request.client else "unknown"

        if not rate_limiter.check(prefix):
            remaining = rate_limiter.remaining(prefix)
            resp = JSONResponse(
                status_code=429,
                content={"detail": "TOO_MANY_REQUESTS", "retry_after": rate_limiter.window},
            )
            resp.headers["X-RateLimit-Remaining"] = str(remaining)
            resp.headers["Retry-After"] = str(rate_limiter.window)
            return resp

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(rate_limiter.remaining(prefix))
        return response
