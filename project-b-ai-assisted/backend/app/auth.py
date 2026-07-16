"""API key authentication.

Creating short URLs requires a valid key in the ``X-API-Key`` header.
Redirects (and stats) are public, so only write endpoints depend on this.
"""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import get_settings

# auto_error=False lets us return a consistent 401 for both missing and
# invalid keys instead of FastAPI's default 403 for a missing header.
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    """FastAPI dependency that rejects requests without a valid API key.

    Uses ``secrets.compare_digest`` for a constant-time comparison so the
    check does not leak key contents through timing differences.
    """

    settings = get_settings()
    if api_key is None or not secrets.compare_digest(api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
