"""
Authentication primitives: password hashing, JWT tokens, refresh tokens, and UA parsing.

Flow:
  register/login -> hash_password / verify_password
  login success -> create_access_token(user.id)  # "sub" claim = user UUID
  login success -> generate_refresh_token()       # URL-safe secret, store hash
  protected routes -> get_token_subject(token) in dependencies.py
  refresh endpoint -> hash_refresh_token(raw) to look up session
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Store only the hash in the database — never the plain password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str | UUID,
    session_id: str | UUID | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Build a signed JWT. subject is the user's id (stored as 'sub' in the payload)."""
    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "sid": str(session_id) if session_id else str(uuid.uuid4()),
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def get_token_subject(token: str) -> UUID:
    """Extract user id from Bearer token; raises JWTError if invalid/expired."""
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise JWTError("Missing subject")
        return UUID(str(subject))
    except (JWTError, ValueError) as exc:
        raise JWTError("Invalid token") from exc


# ── Refresh Token Helpers ────────────────────────────────────────────────────


def generate_refresh_token(session_id: str | UUID | None = None) -> str:
    """
    Generate a cryptographically-secure refresh token (32 bytes = 43 chars).
    If session_id is provided, prefixes with session_id for precise session lookup
    during rotation and instant replay attack detection.
    """
    secret = secrets.token_urlsafe(32)
    if session_id:
        return f"{session_id}.{secret}"
    return secret



def hash_refresh_token(token: str) -> str:
    """SHA-256 hash of the raw token for DB storage. Never store raw tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── User-Agent Parsing ───────────────────────────────────────────────────────


def parse_user_agent(ua_string: str | None) -> dict[str, str | None]:
    """
    Parse a User-Agent string into browser, platform, and device_name.

    Returns dict with keys: browser, platform, device_name.
    Falls back gracefully if user-agents library unavailable.
    """
    if not ua_string:
        return {"browser": None, "platform": None, "device_name": None}

    try:
        from user_agents import parse as ua_parse  # type: ignore[import]

        ua = ua_parse(ua_string)

        browser = ua.browser.family or None
        if browser and ua.browser.version_string:
            browser = f"{browser} {ua.browser.version_string.split('.')[0]}"

        platform = ua.os.family or None

        if ua.is_mobile:
            device_name = ua.device.family or "Mobile Device"
        elif ua.is_tablet:
            device_name = ua.device.family or "Tablet"
        elif ua.is_pc:
            device_name = f"{ua.os.family} PC" if ua.os.family else "Desktop"
        else:
            device_name = ua.device.family or "Unknown Device"

        return {
            "browser": browser,
            "platform": platform,
            "device_name": device_name,
        }
    except Exception:
        return {"browser": None, "platform": None, "device_name": None}
