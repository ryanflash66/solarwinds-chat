"""In-memory sliding-window rate limiter (FastAPI dependency)."""

import time

from fastapi import HTTPException, Request

from app.core.config import settings


class _SlidingWindowRateLimiter:
    """Track request timestamps per client in a sliding 60-second window."""

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = {}

    def _client_key(self, request: Request) -> str:
        """Return a rate-limit key: API key if present, otherwise client IP."""
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key}"
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    async def __call__(self, request: Request) -> None:
        key = self._client_key(request)
        now = time.monotonic()
        window_start = now - 60.0

        # Prune timestamps outside the window; drop idle clients
        timestamps = [t for t in self._requests.get(key, []) if t > window_start]

        if len(timestamps) >= settings.rate_limit_per_minute:
            self._requests[key] = timestamps
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
            )

        timestamps.append(now)
        self._requests[key] = timestamps


rate_limiter = _SlidingWindowRateLimiter()
