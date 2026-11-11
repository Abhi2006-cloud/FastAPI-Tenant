"""
MEMBERSHIPS MODULE — repository.py

get_by_user_and_org is the core query for tenant isolation checks.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.memberships.models import Membership, MembershipRole


class MembershipRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, membership_id: UUID) -> Membership | None:
        result = await self.db.execute(
            select(Membership).where(Membership.id == membership_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_org(
        self, user_id: UUID, organization_id: UUID
    ) -> Membership | None:
        """Returns None if user is NOT in the org -> service raises 403."""
        result = await self.db.execute(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_by_organization(self, organization_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Membership.id)).where(Membership.organization_id == organization_id)
        )
        return result.scalar() or 0

    async def list_by_organization(
        self, organization_id: UUID
    ) -> list[Membership]:
        """List all memberships for an organization, ordered by created_at."""
        result = await self.db.execute(
            select(Membership)
            .where(Membership.organization_id == organization_id)
            .order_by(Membership.id)  # Using id as proxy for created_at ordering
        )
        return list(result.scalars().all())

    async def list_by_organization_with_users(
        self, organization_id: UUID
    ) -> list[Membership]:
        """List memberships with user data joined, ordered by created_at."""
        result = await self.db.execute(
            select(Membership)
            .options(joinedload(Membership.user))
            .where(Membership.organization_id == organization_id)
            .order_by(Membership.id)
        )
        return list(result.scalars().unique().all())

    async def update_role(self, membership_id: UUID, new_role: MembershipRole) -> Membership:
        """Update the role of a membership."""
        membership = await self.get_by_id(membership_id)
        if membership is None:
            return None
        membership.role = new_role
        await self.db.flush()
        await self.db.refresh(membership)
        return membership

    async def delete(self, membership_id: UUID) -> bool:
        """Delete a membership. Returns True if deleted, False if not found."""
        membership = await self.get_by_id(membership_id)
        if membership is None:
            return False
        await self.db.delete(membership)
        await self.db.flush()
        return True

    async def create(
        self,
        user_id: UUID,
        organization_id: UUID,
        role: MembershipRole,
    ) -> Membership:
        membership = Membership(
            user_id=user_id,
            organization_id=organization_id,
            role=role,
        )
        self.db.add(membership)
        await self.db.flush()
        await self.db.refresh(membership)
        return membership
