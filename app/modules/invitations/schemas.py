"""INVITATIONS MODULE — schemas.py."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.invitations.models import InvitationStatus


class InvitationCreate(BaseModel):
    """POST /organizations/{org_id}/invite — email to invite."""

    email: EmailStr


class InvitationResponse(BaseModel):
    """Invitation response model. Includes token and invitation URL in Development Mode."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    organization_id: UUID
    token: str | None = None
    invitation_url: str | None = None
    status: InvitationStatus
    delivery_status: str | None = Field(
        default="manual_sharing_required",
        description="Delivery status: 'email_sent', 'manual_sharing_required', or 'console_logged'",
    )
    delivery_mode: str | None = Field(
        default="development",
        description="Active delivery mode: 'production', 'development', or 'console'",
    )
    message: str | None = Field(
        default=None,
        description="User-facing guidance regarding invitation delivery",
    )
    expires_at: datetime



class InvitationAccept(BaseModel):
    """POST /invitations/accept — body contains token from invite response."""

    token: str = Field(min_length=1, max_length=64)
