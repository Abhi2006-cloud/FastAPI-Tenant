"""
DEMO MODULE — schemas.py

Pydantic models for demo session creation and upgrade.
"""

from uuid import UUID

from pydantic import BaseModel


class DemoSessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    session_id: UUID
    expires_in: int
    organization_id: UUID


class DemoUpgradeResponse(BaseModel):
    organization_id: UUID
    plan: str
    message: str

