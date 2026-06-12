"""
Authentication primitives: password hashing and JWT tokens.

Flow:
  register/login -> hash_password / verify_password
  login success -> create_access_token(user.id)  # "sub" claim = user UUID
  protected routes -> get_token_subject(token) in dependencies.py
"""

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


def create_access_token(subject: str | UUID, expires_delta: timedelta | None = None) -> str:
    """Build a signed JWT. subject is the user's id (stored as 'sub' in the payload)."""
    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode: dict[str, Any] = {"sub": str(subject), "exp": expire}
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
