"""MEMBERSHIPS MODULE — schemas.py (membership API responses)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.memberships.models import MembershipRole


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    organization_id: UUID
    role: MembershipRole


class MemberListResponse(BaseModel):
    """Response for listing organization members with user details."""
    
    model_config = ConfigDict(from_attributes=True)

    membership_id: UUID
    user_id: UUID
    email: str
    role: MembershipRole
    created_at: datetime


class RoleChangeRequest(BaseModel):
    """Request to change a member's role."""
    
    role: MembershipRole = Field(..., description="New role (admin or member)")


class RoleChangeResponse(BaseModel):
    """Response after successful role change."""
    
    membership_id: UUID
    user_id: UUID
    new_role: MembershipRole


class MemberRemoveResponse(BaseModel):
    """Response after successful member removal."""
    
    message: str = "member removed"


class OwnershipTransferRequest(BaseModel):
    """Request to transfer organization ownership."""

    new_owner_membership_id: UUID | None = Field(default=None, description="Membership ID of the new owner")
    new_owner_user_id: UUID | None = Field(default=None, description="User ID of the new owner")

    @model_validator(mode="after")
    def validate_identifier(self) -> "OwnershipTransferRequest":
        if not self.new_owner_membership_id and not self.new_owner_user_id:
            raise ValueError("Either new_owner_membership_id or new_owner_user_id must be provided")
        return self


class OwnershipTransferResponse(BaseModel):
    """Response after successful ownership transfer."""
    
    message: str = "ownership transferred"
