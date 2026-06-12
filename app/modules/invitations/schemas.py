"""INVITATIONS MODULE — schemas.py."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.invitations.models import InvitationStatus


class InvitationCreate(BaseModel):
    """POST /organizations/{org_id}/invite — email to invite."""

    email: EmailStr


class InvitationResponse(BaseModel):
    """Includes token so client can share it (V1 does not send email)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    organization_id: UUID
    token: str
    status: InvitationStatus
    expires_at: datetime


class InvitationAccept(BaseModel):
    """POST /invitations/accept — body contains token from invite response."""

    token: str = Field(min_length=1, max_length=64)
