"""API routes for creating short URLs."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse

from .auth import require_api_key
from .config import get_settings
from .db import get_db
from .schemas import CreateUrlRequest, UrlResponse
from .shortener import generate_code, normalize_url

router = APIRouter()

# Collision handling: with 62^7 (~3.5 trillion) possible codes, even one
# truncation collision is rare; a handful of salted retries is plenty.
_MAX_COLLISION_RETRIES = 10


def _row_to_response(row: sqlite3.Row) -> UrlResponse:
    """Convert a DB row into the public response model."""

    settings = get_settings()
    return UrlResponse(
        short_code=row["short_code"],
        short_url=f"{settings.base_url}/{row['short_code']}",
        long_url=row["long_url"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        click_count=row["click_count"],
    )


@router.post(
    "/api/urls",
    response_model=UrlResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["urls"],
    summary="Create a short URL",
    dependencies=[Depends(require_api_key)],
)
def create_short_url(
    payload: CreateUrlRequest,
    response: Response,
    db: sqlite3.Connection = Depends(get_db),
) -> UrlResponse:
    """Shorten a long URL.

    Returns 201 with the new record, or 200 with the existing record when the
    exact URL was already shortened (idempotent create). Requires X-API-Key.
    """

    settings = get_settings()

    try:
        long_url = normalize_url(payload.url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    if payload.expires_at is not None:
        expires_utc = payload.expires_at
        if expires_utc.tzinfo is not None:
            expires_utc = expires_utc.astimezone(timezone.utc).replace(tzinfo=None)
        if expires_utc <= datetime.now(timezone.utc).replace(tzinfo=None):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="expires_at must be in the future",
            )
        expires_value = expires_utc.strftime("%Y-%m-%d %H:%M:%S")
    else:
        expires_value = None

    # Dedup: the same long URL returns its existing short link.
    existing = db.execute(
        "SELECT * FROM urls WHERE long_url = ?", (long_url,)
    ).fetchone()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return _row_to_response(existing)

    # Hash-derived code; on truncation collision (code taken by a different
    # URL), retry with an incrementing salt.
    for salt in range(_MAX_COLLISION_RETRIES):
        code = generate_code(long_url, settings.short_code_length, salt)
        try:
            db.execute(
                "INSERT INTO urls (long_url, short_code, expires_at) VALUES (?, ?, ?)",
                (long_url, code, expires_value),
            )
            db.commit()
            break
        except sqlite3.IntegrityError:
            continue
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not allocate a unique short code",
        )

    row = db.execute("SELECT * FROM urls WHERE short_code = ?", (code,)).fetchone()
    return _row_to_response(row)


def _is_expired(row: sqlite3.Row) -> bool:
    """True when the row has an expiry timestamp in the past."""

    if row["expires_at"] is None:
        return False
    expires = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
    return expires <= datetime.now(timezone.utc).replace(tzinfo=None)


@router.get(
    "/{short_code}",
    tags=["urls"],
    summary="Redirect to the original URL",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
def redirect_short_url(
    short_code: str,
    db: sqlite3.Connection = Depends(get_db),
) -> RedirectResponse:
    """Resolve a short code and redirect to its long URL. Public.

    Uses 307 so clients do not cache the mapping permanently (a 301 would let
    browsers skip the server — and the click counter — on repeat visits).
    Returns 404 for unknown codes and 410 for expired ones.
    """

    row = db.execute(
        "SELECT * FROM urls WHERE short_code = ?", (short_code,)
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found"
        )
    if _is_expired(row):
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Short URL has expired"
        )

    # Single-statement increment is atomic; concurrent redirects never lose
    # a count the way a read-modify-write would.
    db.execute(
        "UPDATE urls SET click_count = click_count + 1 WHERE short_code = ?",
        (short_code,),
    )
    db.commit()

    return RedirectResponse(
        url=row["long_url"], status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )
