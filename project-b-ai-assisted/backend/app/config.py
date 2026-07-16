"""Application configuration, loaded from environment variables.

Values are read once from the environment (optionally seeded by a local
``.env`` file) and cached. Keeping configuration in a single typed object makes
it easy to inject and to override in tests via ``get_settings.cache_clear()``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# Load a local .env file if present. Real environment variables always win,
# so this is safe to call unconditionally in development and production.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Typed, immutable view of the app's runtime configuration."""

    # Secret required in the X-API-Key header to create short URLs.
    api_key: str
    # Filesystem path to the SQLite database file.
    database_path: str
    # Public base URL used to build the full short link (e.g. http://host/abc123).
    base_url: str
    # Number of characters in a generated short code.
    short_code_length: int


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings.

    Call ``get_settings.cache_clear()`` in tests to force a reload after
    changing environment variables.
    """

    return Settings(
        api_key=os.getenv("API_KEY", "dev-secret-key"),
        database_path=os.getenv("DATABASE_PATH", "urls.db"),
        base_url=os.getenv("BASE_URL", "http://localhost:8000").rstrip("/"),
        short_code_length=int(os.getenv("SHORT_CODE_LENGTH", "7")),
    )
