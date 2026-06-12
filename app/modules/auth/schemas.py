"""
AUTH MODULE — schemas.py

Pydantic models for API input/output. They are NOT database tables.
- *Create / *Login = request bodies
- *Response = what clients see (never exposes password_hash)
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
    """POST /auth/login response — client stores access_token for Bearer auth."""

    access_token: str
    token_type: str = "bearer"
