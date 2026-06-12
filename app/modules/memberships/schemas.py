"""MEMBERSHIPS MODULE — schemas.py (for future membership API responses)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.memberships.models import MembershipRole


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    organization_id: UUID
    role: MembershipRole
