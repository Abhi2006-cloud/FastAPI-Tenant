"""
ORGANIZATIONS MODULE — service.py

Creating an org is a two-step business operation:
  1. Insert Organization (owner_id = creator)
  2. Insert Membership with role OWNER (so creator can access tenant data)

Without step 2, the owner could not use /files or other membership-gated APIs.
"""

from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheKeyBuilder, CacheService, CacheTTL
from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.jobs.tasks import delete_organization_task, index_member_task, index_organization_task
from app.modules.audit.events import RESOURCE_MEMBERSHIP, RESOURCE_ORGANIZATION, AuditAction
from app.modules.audit.service import AuditLogService
from app.modules.files.repository import FileRepository
from app.modules.files.storage import StorageService
from app.modules.memberships.models import MembershipRole
from app.modules.memberships.repository import MembershipRepository
from app.modules.memberships.service import MembershipService
from app.modules.organizations.models import Organization
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.schemas import OrganizationCreate, OrganizationResponse
from app.services.job_service import JobService

settings = get_settings()


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
        if settings.is_search_enabled:
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
        if settings.is_search_enabled:
            self.job_service.enqueue(index_organization_task, str(organization_id))
        
        # Invalidate caches
        user_cache_key = CacheKeyBuilder.user(str(requester_user_id))
        org_cache_key = CacheKeyBuilder.organization(str(organization_id))
        await self.cache.delete(user_cache_key)
        await self.cache.delete(org_cache_key)
        
        return org


    async def list_user_organizations(self, user_id: UUID) -> list[OrganizationResponse]:
        """List all organizations caller belongs to, including caller role and member count."""
        cache_key = CacheKeyBuilder.user(str(user_id))

        async def fetch_from_db():
            orgs = await self.repo.list_for_user(user_id)
            membership_repo = MembershipRepository(self.db)
            results = []
            for org in orgs:
                membership = await membership_repo.get_by_user_and_org(user_id, org.id)
                member_count = await membership_repo.count_by_organization(org.id)
                role_val = membership.role.value if (membership and hasattr(membership.role, "value")) else (str(membership.role) if membership else None)
                resp = OrganizationResponse(
                    id=org.id,
                    name=org.name,
                    owner_id=org.owner_id,
                    created_at=org.created_at,
                    plan=org.plan or "free",
                    plan_updated_at=org.plan_updated_at,
                    role=role_val,
                    member_count=member_count,
                )
                results.append(resp.model_dump(mode="json"))
            return results

        cached_data = await self.cache.get_or_set(
            cache_key,
            fetch_from_db,
            ttl=CacheTTL.MEDIUM,
        )

        return [OrganizationResponse.model_validate(item) for item in cached_data]

    async def get_organization_detail(
        self, user_id: UUID, organization_id: UUID
    ) -> OrganizationResponse:
        """G1: Return organization detail including caller's role and member_count."""
        membership = await self.membership_service.ensure_member(user_id, organization_id)
        org = await self.repo.get_by_id(organization_id)
        if org is None:
            raise NotFoundError("Organization not found")

        membership_repo = MembershipRepository(self.db)
        member_count = await membership_repo.count_by_organization(organization_id)
        role_val = membership.role.value if hasattr(membership.role, "value") else str(membership.role)

        return OrganizationResponse(
            id=org.id,
            name=org.name,
            owner_id=org.owner_id,
            created_at=org.created_at,
            plan=org.plan or "free",
            plan_updated_at=org.plan_updated_at,
            role=role_val,
            member_count=member_count,
        )

    async def leave_organization(self, user_id: UUID, organization_id: UUID) -> None:
        """G5: Leave organization for any non-owner member. Owner must transfer first (400)."""
        membership = await self.membership_service.ensure_member(user_id, organization_id)
        if membership.role == MembershipRole.OWNER:
            raise BadRequestError(
                "Organization owner cannot leave the organization without transferring ownership first"
            )

        await self.membership_service.repo.delete(membership.id)

        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=user_id,
            action=AuditAction.MEMBER_LEFT,
            resource_type=RESOURCE_MEMBERSHIP,
            resource_id=membership.id,
            metadata={"user_id": str(user_id)},
        )

        # Invalidate caches
        user_cache_key = CacheKeyBuilder.user(str(user_id))
        org_cache_key = CacheKeyBuilder.organization(str(organization_id))
        await self.cache.delete(user_cache_key)
        await self.cache.delete(org_cache_key)

    async def delete_organization(
        self, user_id: UUID, organization_id: UUID, confirmed_name: str
    ) -> None:
        """G6: Owner only; body must include exact org name as confirmation. Deletes stored files, search docs, caches, and org."""
        org = await self.repo.get_by_id(organization_id)
        if org is None:
            raise NotFoundError("Organization not found")

        if org.owner_id != user_id:
            raise ForbiddenError("Only the organization owner can delete the organization")

        if confirmed_name != org.name:
            raise BadRequestError(
                f"Confirmation name '{confirmed_name}' does not match organization name '{org.name}'"
            )

        # 1. Delete all stored files via StorageService (including blobs and disk files)
        file_repo = FileRepository(self.db)
        files = await file_repo.list_by_organization(organization_id)
        storage = StorageService(Path(settings.upload_dir), db=self.db)
        for f in files:
            try:
                await storage.async_delete(f.file_path)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning("Failed to delete storage file %s: %s", f.file_path, exc)

        # 2. Audit event before row is deleted (so it references org or gets cascade deleted)
        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=user_id,
            action=AuditAction.ORGANIZATION_DELETED,
            resource_type=RESOURCE_ORGANIZATION,
            resource_id=organization_id,
            metadata={"name": org.name},
        )

        # 3. Search document removal if search enabled
        if settings.is_search_enabled:
            self.job_service.enqueue(delete_organization_task, str(organization_id))

        # 4. Invalidate caches
        user_cache_key = CacheKeyBuilder.user(str(user_id))
        org_cache_key = CacheKeyBuilder.organization(str(organization_id))
        await self.cache.delete(user_cache_key)
        await self.cache.delete(org_cache_key)

        # 5. Delete organization in DB (cascades memberships, invitations, files, blobs, upgrade requests)
        await self.repo.delete(org)
        await self.db.commit()

    async def get_organization_for_member(
        self, user_id: UUID, organization_id: UUID
    ) -> Organization:
        """Load org only if user is a member — used by other modules internally."""
        await self.membership_service.ensure_member(user_id, organization_id)
        organization = await self.repo.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError("Organization not found")
        return organization
