"""
ORGANIZATIONS MODULE — service.py

Creating an org is a two-step business operation:
  1. Insert Organization (owner_id = creator)
  2. Insert Membership with role OWNER (so creator can access tenant data)

Without step 2, the owner could not use /files or other membership-gated APIs.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheKeyBuilder, CacheService, CacheTTL
from app.core.exceptions import NotFoundError
from app.modules.audit.events import RESOURCE_ORGANIZATION, AuditAction
from app.modules.audit.service import AuditLogService
from app.modules.memberships.models import MembershipRole
from app.modules.memberships.service import MembershipService
from app.modules.organizations.models import Organization
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.schemas import OrganizationCreate, OrganizationResponse
from app.services.job_service import JobService
from app.jobs.tasks import index_organization_task, index_member_task


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OrganizationRepository(db)
        self.membership_service = MembershipService(db)
        self.cache = CacheService()
        self.job_service = JobService()

    async def create_organization(
        self, owner_id: UUID, data: OrganizationCreate
    ) -> Organization:
        organization = await self.repo.create(name=data.name, owner_id=owner_id)
        owner_membership = await self.membership_service.add_member(
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
        await self.db.commit()
        
        # Enqueue search indexing tasks for the organization and owner membership
        self.job_service.enqueue(index_organization_task, str(organization.id))
        self.job_service.enqueue(index_member_task, str(owner_membership.id))

        # Invalidate user's organization list cache
        cache_key = CacheKeyBuilder.user(str(owner_id))
        await self.cache.delete(cache_key)
        return organization

    async def rename_organization(
        self, requester_user_id: UUID, organization_id: UUID, new_name: str
    ) -> Organization:
        """Rename an organization, log audit event, enqueue search indexing, invalidate cache."""
        # Enforce OWNER or ADMIN role
        await self.membership_service.ensure_roles(
            requester_user_id, organization_id, {MembershipRole.OWNER, MembershipRole.ADMIN}
        )
        
        org = await self.repo.get_by_id(organization_id)
        if org is None:
            raise NotFoundError("Organization not found")
            
        old_name = org.name
        org.name = new_name
        
        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=requester_user_id,
            action=AuditAction.ORGANIZATION_RENAMED,
            resource_type=RESOURCE_ORGANIZATION,
            resource_id=organization_id,
            metadata={"old_name": old_name, "new_name": new_name},
        )
        
        # Enqueue search indexing task for organization update
        self.job_service.enqueue(index_organization_task, str(organization_id))
        
        # Invalidate caches
        user_cache_key = CacheKeyBuilder.user(str(requester_user_id))
        org_cache_key = CacheKeyBuilder.organization(str(organization_id))
        await self.cache.delete(user_cache_key)
        await self.cache.delete(org_cache_key)
        
        return org


    async def list_user_organizations(self, user_id: UUID) -> list[Organization]:
        cache_key = CacheKeyBuilder.user(str(user_id))
        
        async def fetch_from_db():
            orgs = await self.repo.list_for_user(user_id)
            return [OrganizationResponse.model_validate(org).model_dump() for org in orgs]
        
        cached_data = await self.cache.get_or_set(
            cache_key,
            fetch_from_db,
            ttl=CacheTTL.MEDIUM,
        )
        
        # Convert back to Organization objects
        return [Organization(**org_data) for org_data in cached_data]

    async def get_organization_for_member(
        self, user_id: UUID, organization_id: UUID
    ) -> Organization:
        """Load org only if user is a member — used by other modules internally."""
        await self.membership_service.ensure_member(user_id, organization_id)
        organization = await self.repo.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError("Organization not found")
        return organization
