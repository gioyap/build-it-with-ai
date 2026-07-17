"""Behavioral tests for the URL shortener API.

Each test gets a fresh database via the ``client`` fixture, so tests are
independent and order-insensitive.
"""

from __future__ import annotations

LONG_URL = "https://example.com/some/long/path?q=1"


# ---------------------------------------------------------------- auth

def test_create_requires_api_key(client):
    response = client.post("/api/urls", json={"url": LONG_URL})
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "ApiKey"


def test_create_rejects_wrong_api_key(client):
    response = client.post(
        "/api/urls", json={"url": LONG_URL}, headers={"X-API-Key": "nope"}
    )
    assert response.status_code == 401


# -------------------------------------------------------------- create

def test_create_short_url(client, auth_headers):
    response = client.post("/api/urls", json={"url": LONG_URL}, headers=auth_headers)
    assert response.status_code == 201

    body = response.json()
    assert body["long_url"] == LONG_URL
    assert body["click_count"] == 0
    assert body["expires_at"] is None
    assert len(body["short_code"]) == 7
    assert body["short_url"].endswith("/" + body["short_code"])


def test_duplicate_url_returns_existing_code(client, auth_headers):
    first = client.post("/api/urls", json={"url": LONG_URL}, headers=auth_headers)
    second = client.post("/api/urls", json={"url": LONG_URL}, headers=auth_headers)

    assert first.status_code == 201
    assert second.status_code == 200  # existing record, not a new one
    assert second.json()["short_code"] == first.json()["short_code"]


def test_different_urls_get_different_codes(client, auth_headers):
    a = client.post("/api/urls", json={"url": "https://example.com/a"}, headers=auth_headers)
    b = client.post("/api/urls", json={"url": "https://example.com/b"}, headers=auth_headers)
    assert a.json()["short_code"] != b.json()["short_code"]


def test_invalid_urls_are_rejected(client, auth_headers):
    invalid = [
        "not-a-url",
        "ftp://example.com/file",
        "javascript:alert(1)",
        "http://",
        "   ",
        "https://example.com/" + "a" * 3000,  # over the 2048-char cap
    ]
    for url in invalid:
        response = client.post("/api/urls", json={"url": url}, headers=auth_headers)
        assert response.status_code == 422, url


def test_expiry_must_be_in_the_future(client, auth_headers):
    response = client.post(
        "/api/urls",
        json={"url": LONG_URL, "expires_at": "2020-01-01T00:00:00Z"},
        headers=auth_headers,
    )
    assert response.status_code == 422


# ------------------------------------------------------------ redirect

def test_redirect_returns_307_to_long_url(client, auth_headers):
    code = client.post(
        "/api/urls", json={"url": LONG_URL}, headers=auth_headers
    ).json()["short_code"]

    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == LONG_URL


def test_redirect_is_public(client, auth_headers):
    code = client.post(
        "/api/urls", json={"url": LONG_URL}, headers=auth_headers
    ).json()["short_code"]

    # No API key on the redirect request.
    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 307


def test_unknown_code_returns_404(client):
    response = client.get("/doesnot1", follow_redirects=False)
    assert response.status_code == 404


def test_expired_code_returns_410_and_counts_no_click(client, auth_headers):
    code = client.post(
        "/api/urls",
        json={"url": LONG_URL, "expires_at": "2030-01-01T00:00:00Z"},
        headers=auth_headers,
    ).json()["short_code"]

    # Expire it directly in the database.
    import sqlite3
    from app.config import get_settings

    db = sqlite3.connect(get_settings().database_path)
    db.execute(
        "UPDATE urls SET expires_at = '2020-01-01 00:00:00' WHERE short_code = ?",
        (code,),
    )
    db.commit()
    db.close()

    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 410

    stats = client.get(f"/api/urls/{code}/stats")
    assert stats.json()["click_count"] == 0


# --------------------------------------------------------------- stats

def test_click_count_increments_per_redirect(client, auth_headers):
    code = client.post(
        "/api/urls", json={"url": LONG_URL}, headers=auth_headers
    ).json()["short_code"]

    for _ in range(3):
        client.get(f"/{code}", follow_redirects=False)

    stats = client.get(f"/api/urls/{code}/stats")
    assert stats.status_code == 200
    assert stats.json()["click_count"] == 3


def test_stats_for_unknown_code_returns_404(client):
    response = client.get("/api/urls/doesnot1/stats")
    assert response.status_code == 404


def test_list_urls_requires_key_and_returns_all(client, auth_headers):
    client.post("/api/urls", json={"url": "https://example.com/a"}, headers=auth_headers)
    client.post("/api/urls", json={"url": "https://example.com/b"}, headers=auth_headers)

    assert client.get("/api/urls").status_code == 401

    response = client.get("/api/urls", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2
