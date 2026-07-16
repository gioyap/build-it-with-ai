"""FastAPI application entry point.

Phase 1 provides the application scaffold and configuration wiring only.
Data persistence and the URL/redirect/stats endpoints are added in later phases.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import __version__
from .config import get_settings
from .db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Ensure the database schema exists before the app serves requests."""

    init_db()
    yield


app = FastAPI(
    title="URL Shortener API",
    description=(
        "Create short URLs from long ones, redirect visitors, and track click "
        "counts. Creating URLs requires an API key; redirects are public."
    ),
    version=__version__,
    lifespan=lifespan,
)


@app.get("/health", tags=["meta"], summary="Liveness check")
def health() -> dict[str, str]:
    """Return a simple OK payload so callers can confirm the API is running."""

    return {"status": "ok"}


@app.get("/", tags=["meta"], summary="Service metadata")
def root() -> dict[str, str]:
    """Return basic service metadata and a pointer to the interactive docs."""

    settings = get_settings()
    return {
        "name": app.title,
        "version": app.version,
        "base_url": settings.base_url,
        "docs": "/docs",
    }
