"""Short-code generation and URL validation.

Codes are derived from a SHA-256 hash of the long URL, encoded in base62 and
truncated to the configured length. Hashing (rather than random codes) gives
deterministic dedup for free: the same URL always maps to the same code.

Truncation means two different URLs can collide. The caller resolves this by
retrying with an incrementing salt appended to the hash input until a free
(or matching) code is found.
"""

from __future__ import annotations

import hashlib
from urllib.parse import urlparse

_BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

# Practical ceiling shared by browsers and CDNs; also caps hash input size.
MAX_URL_LENGTH = 2048


def normalize_url(raw: str) -> str:
    """Validate a URL and return its normalized form.

    Accepts only absolute http/https URLs with a hostname. Raises
    ``ValueError`` with a human-readable message otherwise.
    """

    candidate = raw.strip()
    if not candidate:
        raise ValueError("URL must not be empty")
    if len(candidate) > MAX_URL_LENGTH:
        raise ValueError(f"URL must be at most {MAX_URL_LENGTH} characters")

    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://")
    if not parsed.netloc or not parsed.hostname:
        raise ValueError("URL must include a valid host")
    if "." not in parsed.hostname and parsed.hostname != "localhost":
        raise ValueError("URL host looks invalid")

    return candidate


def generate_code(long_url: str, length: int, salt: int = 0) -> str:
    """Derive a base62 short code from a hash of ``long_url``.

    ``salt`` alters the hash input to produce a different code when a
    truncation collision occurs (same code, different URL).
    """

    payload = long_url if salt == 0 else f"{long_url}#{salt}"
    digest = hashlib.sha256(payload.encode("utf-8")).digest()

    # Interpret the digest as a big integer and re-encode it in base62,
    # taking the first `length` characters.
    number = int.from_bytes(digest, "big")
    chars = []
    while number and len(chars) < length:
        number, rem = divmod(number, 62)
        chars.append(_BASE62[rem])
    return "".join(chars).rjust(length, _BASE62[0])
