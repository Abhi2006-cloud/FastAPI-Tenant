"""
MEMBERSHIPS MODULE — service.py

Central place for tenant access rules. Other modules call:
  - ensure_member      before reading/writing org data
  - ensure_roles       before admin actions (invites)
  - add_member         on org create or invite accept
  - list_members       for member management UI
  - change_role        for role changes
  - remove_member      for member removal
  - transfer_ownership for ownership transfer
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.modules.audit.events import RESOURCE_MEMBERSHIP, AuditAction
from app.modules.audit.service import AuditLogService
from app.modules.memberships.models import Membership, MembershipRole
from app.modules.memberships.repository import MembershipRepository


class MembershipService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
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

    async def list_members(
        self,
        requester_user_id: UUID,
        organization_id: UUID,
    ) -> list[Membership]:
        """
        List all members of an organization.
        
        Args:
            requester_user_id: User requesting the list
            organization_id: Organization to list members for
            
        Returns:
            List of memberships with user data joined
            
        Raises:
            ForbiddenError: If requester is not a member of the organization
        """
        # Ensure requester is a member
        await self.ensure_member(requester_user_id, organization_id)
        
        # List all memberships with user data
        return await self.repo.list_by_organization_with_users(organization_id)

    async def change_role(
        self,
        requester_user_id: UUID,
        organization_id: UUID,
        membership_id: UUID,
        new_role: MembershipRole,
    ) -> Membership:
        """
        Change a member's role.
        
        Rules:
        - Only owner can change roles
        - Owner cannot be assigned directly (use transfer_ownership)
        - Cannot modify organization owner role
        - Invalid role returns 400
        
        Args:
            requester_user_id: User requesting the role change
            organization_id: Organization context
            membership_id: Membership to modify
            new_role: New role to assign (admin or member)
            
        Returns:
            Updated membership
            
        Raises:
            ForbiddenError: If requester lacks permissions
            BadRequestError: If role is invalid or trying to modify owner
            NotFoundError: If membership not found
        """
        # Validate new role
        if new_role == MembershipRole.OWNER:
            raise BadRequestError("Cannot assign owner role directly. Use ownership transfer.")
        
        if new_role not in {MembershipRole.ADMIN, MembershipRole.MEMBER}:
            raise BadRequestError("Invalid role. Must be admin or member.")
        
        # Ensure requester is owner
        await self.ensure_roles(requester_user_id, organization_id, {MembershipRole.OWNER})
        
        # Get target membership
        target_membership = await self.repo.get_by_id(membership_id)
        if target_membership is None:
            raise NotFoundError("Membership not found")
        
        # Ensure target belongs to the organization
        if target_membership.organization_id != organization_id:
            raise ForbiddenError("Membership does not belong to this organization")
        
        # Cannot modify owner role
        if target_membership.role == MembershipRole.OWNER:
            raise BadRequestError("Cannot modify organization owner role")

        old_role = target_membership.role
        updated = await self.repo.update_role(membership_id, new_role)
        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=requester_user_id,
            action=AuditAction.MEMBER_ROLE_CHANGED,
            resource_type=RESOURCE_MEMBERSHIP,
            resource_id=membership_id,
            metadata={
                "target_user_id": str(target_membership.user_id),
                "old_role": old_role.value,
                "new_role": new_role.value,
            },
        )
        return updated

    async def remove_member(
        self,
        requester_user_id: UUID,
        organization_id: UUID,
        membership_id: UUID,
    ) -> None:
        """
        Remove a member from the organization.
        
        Rules:
        - Only owner can remove members
        - Owner cannot remove themselves
        - Owner membership cannot be deleted
        
        Args:
            requester_user_id: User requesting removal
            organization_id: Organization context
            membership_id: Membership to remove
            
        Raises:
            ForbiddenError: If requester lacks permissions or trying to remove owner
            NotFoundError: If membership not found
        """
        # Ensure requester is owner
        await self.ensure_roles(requester_user_id, organization_id, {MembershipRole.OWNER})
        
        # Get target membership
        target_membership = await self.repo.get_by_id(membership_id)
        if target_membership is None:
            raise NotFoundError("Membership not found")
        
        # Ensure target belongs to the organization
        if target_membership.organization_id != organization_id:
            raise ForbiddenError("Membership does not belong to this organization")
        
        # Cannot remove owner
        if target_membership.role == MembershipRole.OWNER:
            raise ForbiddenError("Cannot remove organization owner")
        
        # Cannot remove self
        if target_membership.user_id == requester_user_id:
            raise ForbiddenError("Cannot remove yourself from the organization")

        removed_user_id = target_membership.user_id
        removed_role = target_membership.role.value

        # Delete membership
        await self.repo.delete(membership_id)
        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=requester_user_id,
            action=AuditAction.MEMBER_REMOVED,
            resource_type=RESOURCE_MEMBERSHIP,
            resource_id=membership_id,
            metadata={
                "target_user_id": str(removed_user_id),
                "removed_role": removed_role,
            },
        )

    async def transfer_ownership(
        self,
        requester_user_id: UUID,
        organization_id: UUID,
        new_owner_membership_id: UUID,
    ) -> None:
        """
        Transfer organization ownership to another member.
        
        Rules:
        - Only current owner can transfer ownership
        - Target must be a member of the organization
        - Target cannot already be owner
        
        Behavior:
        - Current owner becomes admin
        - Target becomes owner
        - Transactional (rollback on failure)
        
        Args:
            requester_user_id: User requesting transfer
            organization_id: Organization context
            new_owner_membership_id: Membership ID of new owner
            
        Raises:
            ForbiddenError: If requester lacks permissions or invalid target
            NotFoundError: If target membership not found
        """
        # Ensure requester is owner
        await self.ensure_roles(requester_user_id, organization_id, {MembershipRole.OWNER})
        
        # Get current owner membership
        current_owner_membership = await self.repo.get_by_user_and_org(
            requester_user_id, organization_id
        )
        if current_owner_membership is None:
            raise ForbiddenError("You are not the owner of this organization")
        
        # Get target membership
        target_membership = await self.repo.get_by_id(new_owner_membership_id)
        if target_membership is None:
            raise NotFoundError("Target membership not found")
        
        # Ensure target belongs to the organization
        if target_membership.organization_id != organization_id:
            raise ForbiddenError("Target membership does not belong to this organization")
        
        # Target cannot already be owner and cannot be self
        if target_membership.role == MembershipRole.OWNER:
            raise BadRequestError("Target is already the owner")
        
        if target_membership.user_id == requester_user_id:
            raise BadRequestError("Cannot transfer ownership to yourself")
        
        # Perform transfer transactionally
        # Current owner -> admin
        await self.repo.update_role(current_owner_membership.id, MembershipRole.ADMIN)

        # Target -> owner
        await self.repo.update_role(target_membership.id, MembershipRole.OWNER)
        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=requester_user_id,
            action=AuditAction.OWNERSHIP_TRANSFERRED,
            resource_type=RESOURCE_MEMBERSHIP,
            resource_id=target_membership.id,
            metadata={
                "previous_owner_id": str(requester_user_id),
                "new_owner_id": str(target_membership.user_id),
                "new_owner_membership_id": str(target_membership.id),
            },
        )
