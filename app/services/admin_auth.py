import base64
import hashlib
import hmac
import time

from fastapi import HTTPException, status

from app.core.config import settings


def admin_enabled() -> bool:
    return bool(settings.ADMIN_USERNAME and settings.ADMIN_PASSWORD and settings.ADMIN_SESSION_SECRET)


def verify_credentials(username: str, password: str) -> bool:
    if not admin_enabled():
        return False
    return username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD


def create_admin_token() -> str:
    if not admin_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin not configured")
    expires_at = int(time.time()) + settings.ADMIN_SESSION_TTL_SECONDS
    payload = f"admin:{expires_at}".encode()
    signature = hmac.new(
        settings.ADMIN_SESSION_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(payload + b"." + signature).decode()


def verify_admin_token(token: str) -> bool:
    if not admin_enabled() or not token:
        return False
    try:
        raw = base64.urlsafe_b64decode(token.encode())
        payload_bytes, signature = raw.rsplit(b".", 1)
        expected = hmac.new(
            settings.ADMIN_SESSION_SECRET.encode(),
            payload_bytes,
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(signature, expected):
            return False
        payload = payload_bytes.decode()
        if not payload.startswith("admin:"):
            return False
        expires_at = int(payload.split(":", 1)[1])
        return expires_at >= int(time.time())
    except Exception:
        return False
