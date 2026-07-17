"""Shared fixtures: isolated app + database per test."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make the backend package importable when running pytest from anywhere.
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

TEST_API_KEY = "test-api-key"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient wired to a fresh SQLite database in a temp directory.

    The context-manager form runs the lifespan handler, which creates the
    schema — the same path production startup takes.
    """

    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))

    from app.config import get_settings

    get_settings.cache_clear()

    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


@pytest.fixture()
def auth_headers():
    """Headers carrying the valid test API key."""

    return {"X-API-Key": TEST_API_KEY}
