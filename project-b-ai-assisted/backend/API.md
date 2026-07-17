# URL Shortener — API Reference

Interactive docs (Swagger UI) are auto-generated at **`/docs`** when the server
is running; the raw OpenAPI schema is at `/openapi.json`. This file is the
human-readable summary.

## Authentication

Write endpoints require an API key in the `X-API-Key` header. The key is
configured through the `API_KEY` environment variable (see `.env.example`).

| Endpoint | Auth |
|---|---|
| `POST /api/urls` | **Required** |
| `GET /api/urls` | **Required** |
| `GET /{short_code}` | Public |
| `GET /api/urls/{short_code}/stats` | Public |

Failed auth returns `401` with `WWW-Authenticate: ApiKey`.

---

## `POST /api/urls` — Create a short URL

**Headers:** `X-API-Key: <key>`, `Content-Type: application/json`

**Body:**

```json
{
  "url": "https://example.com/some/very/long/path?with=params",
  "expires_at": "2030-01-01T00:00:00Z"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `url` | string | yes | Absolute `http`/`https` URL, ≤ 2048 chars |
| `expires_at` | ISO 8601 datetime | no | Must be in the future (UTC); omit for a link that never expires |

**Responses:**

| Status | Meaning |
|---|---|
| `201 Created` | New short URL created |
| `200 OK` | This exact URL was already shortened — existing record returned (idempotent) |
| `401` | Missing/invalid API key |
| `422` | Invalid URL (bad scheme, no host, too long, dangerous scheme) or past `expires_at` |

**Response body (201/200):**

```json
{
  "short_code": "Ar7m9B4",
  "short_url": "http://localhost:8000/Ar7m9B4",
  "long_url": "https://example.com/some/very/long/path?with=params",
  "created_at": "2026-07-17T04:05:06",
  "expires_at": null,
  "click_count": 0
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/api/urls \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/long/path"}'
```

---

## `GET /{short_code}` — Redirect (public)

Resolves the code, **increments its click count**, and redirects.

| Status | Meaning |
|---|---|
| `307 Temporary Redirect` | `Location` header carries the original URL |
| `404` | Unknown short code |
| `410 Gone` | Link has expired (click not counted) |

307 (not 301) is deliberate: browsers re-request through the server each time,
so every visit is counted.

```bash
curl -i http://localhost:8000/Ar7m9B4
# HTTP/1.1 307 Temporary Redirect
# location: https://example.com/long/path
```

---

## `GET /api/urls/{short_code}/stats` — Stats (public)

Returns the same record shape as create, with the current `click_count`.

| Status | Meaning |
|---|---|
| `200` | Record returned |
| `404` | Unknown short code |

```bash
curl http://localhost:8000/api/urls/Ar7m9B4/stats
```

---

## `GET /api/urls` — List all short URLs

Requires `X-API-Key`. Returns every record, newest first — backs the dashboard.

```bash
curl http://localhost:8000/api/urls -H "X-API-Key: dev-secret-key"
```

---

## Meta endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness check → `{"status": "ok"}` |
| `GET /` | Service name, version, base URL, docs pointer |

## Error shape

All errors use FastAPI's standard envelope:

```json
{ "detail": "Short URL not found" }
```

## Design notes

- **Short codes** are the first 7 base62 characters of a SHA-256 hash of the
  URL — deterministic, so the same URL always yields the same code (free
  dedup). Truncation collisions between different URLs are resolved by
  retrying with a salt.
- **Duplicates** return the existing record with `200` instead of erroring,
  making create idempotent for clients.
- **Click counting** is a single atomic `UPDATE … SET click_count = click_count + 1`,
  so concurrent redirects don't lose counts.
