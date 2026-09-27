"""Short-lived, signed LAN links to completed downloads."""
from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse

from app.config import settings


def _signature(user: str, expires: int) -> str:
    payload = f"download-link-v1\n{user}\n{expires}".encode()
    return hmac.new(settings.jwt_secret.encode(), payload, hashlib.sha256).hexdigest()


def valid_signature(user: str, expires: int, signature: str, now: int | None = None) -> bool:
    current = int(time.time()) if now is None else now
    if expires < current or expires > current + settings.download_link_ttl_seconds + 60:
        return False
    return hmac.compare_digest(_signature(user, expires), signature)


def user_url(user: str, now: int | None = None) -> str:
    """Return a signed URL to a user's completed-download directory, or ``""``."""
    base = settings.download_base_url.strip().rstrip("/")
    if not base:
        return ""
    current = int(time.time()) if now is None else now
    expires = current + settings.download_link_ttl_seconds
    quoted = urllib.parse.quote(user, safe="")
    return f"{base}/downloads/{quoted}?expires={expires}&sig={_signature(user, expires)}"
