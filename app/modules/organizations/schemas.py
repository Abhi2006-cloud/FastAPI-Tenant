"""ORGANIZATIONS MODULE — schemas.py (API request/response shapes)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrganizationCreate(BaseModel):
    """POST /organizations body."""

    name: str = Field(min_length=1, max_length=255)


class OrganizationResponse(BaseModel):
    """Returned after create or in GET /organizations/my / GET /organizations/{org_id}."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime
    plan: str = "free"
    plan_updated_at: datetime | None = None
    role: str | None = None
    member_count: int | None = None


class OrganizationUpdate(BaseModel):
    """PATCH /organizations/{org_id} body."""
    name: str = Field(min_length=1, max_length=255)


class OrganizationDeleteConfirmation(BaseModel):
    """DELETE /organizations/{org_id} body."""
    name: str = Field(min_length=1, max_length=255)

