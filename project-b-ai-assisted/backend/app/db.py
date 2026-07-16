"""SQLite persistence layer.

Uses the standard-library ``sqlite3`` module directly (no ORM). Connections are
short-lived and created per unit of work: FastAPI runs sync endpoints in a
thread pool, so a fresh connection per request keeps things simple and avoids
cross-thread sharing issues.

The ``urls`` table is the single source of truth for short links:

    id           INTEGER  surrogate primary key
    long_url     TEXT     the original URL being shortened
    short_code   TEXT     unique code used in the short link (indexed via UNIQUE)
    created_at   TEXT     UTC creation timestamp (SQLite CURRENT_TIMESTAMP)
    expires_at   TEXT     optional UTC expiry timestamp; NULL means never expires
    click_count  INTEGER  number of times the short link has been resolved
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import get_settings

# Schema is declared idempotently so init_db() is safe to run on every startup.
SCHEMA = """
CREATE TABLE IF NOT EXISTS urls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    long_url    TEXT    NOT NULL,
    short_code  TEXT    NOT NULL UNIQUE,
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at  TEXT,
    click_count INTEGER NOT NULL DEFAULT 0
);
"""


def _connect() -> sqlite3.Connection:
    """Open a configured SQLite connection.

    ``check_same_thread=False`` lets the connection be handed to FastAPI's
    worker thread. ``row_factory`` gives dict-like access to columns by name.
    """

    settings = get_settings()
    conn = sqlite3.connect(settings.database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Context manager yielding a connection and closing it afterwards."""

    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency yielding a per-request connection.

    Usage in an endpoint:

        def endpoint(db: sqlite3.Connection = Depends(get_db)):
            ...
    """

    with get_connection() as conn:
        yield conn


def init_db() -> None:
    """Create the database schema if it does not already exist."""

    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.commit()
