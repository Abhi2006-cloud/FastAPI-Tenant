"""
AUTH MODULE — schemas.py

Pydantic models for API input/output. They are NOT database tables.
- *Create / *Login = request bodies
- *Response = what clients see (never exposes password_hash)

v2.4.0: Extended TokenResponse with refresh_token + session_id.
        New schemas: RefreshRequest, LogoutRequest, LogoutAllRequest,
                     SessionResponse, SessionListResponse.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    """POST /auth/register body."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """POST /auth/login body."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Safe user object returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    created_at: datetime


class TokenResponse(BaseModel):
    """
    POST /auth/login and POST /auth/refresh response.

    access_token: short-lived JWT (Bearer) — use on protected endpoints
    refresh_token: long-lived opaque secret — use ONLY on /auth/refresh and /auth/logout
    session_id: identifies the current device session
    expires_in: seconds until access_token expires (hint for clients)
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    session_id: UUID
    expires_in: int = 900  # 15 minutes in seconds


# ── Session management request schemas ──────────────────────────────────────


class RefreshRequest(BaseModel):
    """POST /auth/refresh body."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """POST /auth/logout body."""

    refresh_token: str


class LogoutAllRequest(BaseModel):
    """POST /auth/logout-all body."""

    refresh_token: str | None = None
    keep_current: bool = Field(
        default=True,
        description="When True, the session identified by refresh_token is kept alive.",
    )


# ── Session listing response schemas ────────────────────────────────────────


class SessionResponse(BaseModel):
    """Single session row returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_name: str | None
    platform: str | None
    browser: str | None
    ip_address: str | None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    is_current: bool = False  # set by service layer
    is_active: bool


class SessionListResponse(BaseModel):
    """GET /auth/sessions response."""

    sessions: list[SessionResponse]
    total: int
