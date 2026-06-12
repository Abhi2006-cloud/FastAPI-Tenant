"""
MEMBERSHIPS MODULE — service.py

Central place for tenant access rules. Other modules call:
  - ensure_member      before reading/writing org data
  - ensure_roles       before admin actions (invites)
  - add_member         on org create or invite accept

No HTTP routes in V1 (router.py is empty); logic is reused by orgs/invites/files.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError
from app.modules.memberships.models import Membership, MembershipRole
from app.modules.memberships.repository import MembershipRepository


class MembershipService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = MembershipRepository(db)

    async def ensure_member(
        self, user_id: UUID, organization_id: UUID
    ) -> Membership:
        """403 if no membership row exists for this user+org pair."""
        membership = await self.repo.get_by_user_and_org(user_id, organization_id)
        if membership is None:
            raise ForbiddenError("You are not a member of this organization")
        return membership

    async def ensure_roles(
        self,
        user_id: UUID,
        organization_id: UUID,
        allowed_roles: set[MembershipRole],
    ) -> Membership:
        """403 if member but role not in allowed_roles (e.g. member cannot invite)."""
        membership = await self.ensure_member(user_id, organization_id)
        if membership.role not in allowed_roles:
            raise ForbiddenError("Insufficient permissions for this action")
        return membership

    async def add_member(
        self,
        user_id: UUID,
        organization_id: UUID,
        role: MembershipRole,
    ) -> Membership:
        """409 if already a member."""
        existing = await self.repo.get_by_user_and_org(user_id, organization_id)
        if existing is not None:
            raise ConflictError("User is already a member of this organization")
        return await self.repo.create(user_id, organization_id, role)
