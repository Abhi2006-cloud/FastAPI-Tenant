"""
ORGANIZATIONS MODULE — repository.py

SQL for organizations. list_for_user joins memberships so we only return
orgs the user belongs to (tenant list for the workspace switcher).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.memberships.models import Membership
from app.modules.organizations.models import Organization


class OrganizationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, owner_id: UUID) -> Organization:
        organization = Organization(name=name, owner_id=owner_id)
        self.db.add(organization)
        await self.db.flush()
        await self.db.refresh(organization)
        return organization

    async def list_for_user(self, user_id: UUID) -> list[Organization]:
        """All tenants (workspaces) this user is a member of."""
        result = await self.db.execute(
            select(Organization)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(Membership.user_id == user_id)
            .options(selectinload(Organization.memberships))
            .order_by(Organization.created_at.desc())
        )
        return list(result.scalars().unique().all())
