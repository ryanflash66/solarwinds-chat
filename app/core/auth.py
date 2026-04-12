"""API key authentication dependency."""

import secrets

from fastapi import HTTPException, Request

from app.core.config import settings


async def require_api_key(request: Request) -> None:
    """Validate the X-API-Key header against the configured API key.

    If ``settings.api_key`` is *None* (the default), authentication is
    skipped entirely so local development works without extra setup.
    """
    if settings.api_key is None:
        return

    provided = request.headers.get("X-API-Key", "")
    if not provided or not secrets.compare_digest(provided, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
