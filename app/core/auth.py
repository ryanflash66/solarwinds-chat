"""API key authentication module."""

from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

# API key header scheme (auto_error=False so we can handle missing keys ourselves)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> Optional[str]:
    """
    Verify the API key from the request header.

    If ``settings.api_key`` is not configured (None or empty), authentication
    is disabled and all requests pass through.  Otherwise the caller must
    supply a matching ``X-API-Key`` header.
    """
    configured_key = settings.api_key

    # No key configured -- auth disabled
    if not configured_key:
        return None

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    if api_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return api_key
