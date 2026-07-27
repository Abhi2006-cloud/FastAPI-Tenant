"""
ORGANIZATIONS MODULE — service.py

Creating an org is a two-step business operation:
  1. Insert Organization (owner_id = creator)
  2. Insert Membership with role OWNER (so creator can access tenant data)

Without step 2, the owner could not use /files or other membership-gated APIs.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.audit.events import RESOURCE_ORGANIZATION, AuditAction
from app.modules.audit.service import AuditLogService
from app.modules.memberships.models import MembershipRole
from app.modules.memberships.service import MembershipService
from app.modules.organizations.models import Organization
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.schemas import OrganizationCreate


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OrganizationRepository(db)
        self.membership_service = MembershipService(db)

    async def create_organization(
        self, owner_id: UUID, data: OrganizationCreate
    ) -> Organization:
        organization = await self.repo.create(name=data.name, owner_id=owner_id)
        await self.membership_service.add_member(
            user_id=owner_id,
            organization_id=organization.id,
            role=MembershipRole.OWNER,
        )
        await AuditLogService(self.db).create_event(
            organization_id=organization.id,
            actor_user_id=owner_id,
            action=AuditAction.ORGANIZATION_CREATED,
            resource_type=RESOURCE_ORGANIZATION,
            resource_id=organization.id,
            metadata={"name": data.name},
        )
        return organization

    async def list_user_organizations(self, user_id: UUID) -> list[Organization]:
        return await self.repo.list_for_user(user_id)

    async def get_organization_for_member(
        self, user_id: UUID, organization_id: UUID
    ) -> Organization:
        """Load org only if user is a member — used by other modules internally."""
        await self.membership_service.ensure_member(user_id, organization_id)
        organization = await self.repo.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError("Organization not found")
        return organization
