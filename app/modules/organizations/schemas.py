"""ORGANIZATIONS MODULE — schemas.py (API request/response shapes)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrganizationCreate(BaseModel):
    """POST /organizations body."""

    name: str = Field(min_length=1, max_length=255)


class OrganizationResponse(BaseModel):
    """Returned after create or in GET /organizations/my."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime


class OrganizationUpdate(BaseModel):
    """PATCH /organizations/{org_id} body."""
    name: str = Field(min_length=1, max_length=255)

