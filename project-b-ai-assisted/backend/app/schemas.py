"""Pydantic request/response models for the API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateUrlRequest(BaseModel):
    """Payload for creating a short URL."""

    url: str = Field(
        ...,
        description="Absolute http(s) URL to shorten",
        examples=["https://example.com/some/very/long/path?with=params"],
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional UTC expiry; the short link stops working after this",
    )


class UrlResponse(BaseModel):
    """A short URL record as returned by the API."""

    short_code: str
    short_url: str
    long_url: str
    created_at: datetime
    expires_at: datetime | None
    click_count: int
