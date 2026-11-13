"""
MEMBERSHIPS MODULE — router.py

Membership management endpoints:
  - GET /organizations/{org_id}/members - List organization members
  - PATCH /organizations/{org_id}/members/{membership_id}/role - Change member role
  - DELETE /organizations/{org_id}/members/{membership_id} - Remove member
  - POST /organizations/{org_id}/transfer-ownership - Transfer ownership
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.memberships.schemas import (
    MemberListResponse,
    MemberRemoveResponse,
    OwnershipTransferRequest,
    OwnershipTransferResponse,
    RoleChangeRequest,
    RoleChangeResponse,
)
from app.modules.memberships.service import MembershipService

router = APIRouter(prefix="/organizations", tags=["memberships"])


@router.get("/{org_id}/members", response_model=list[MemberListResponse])
async def list_organization_members(
    org_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[MemberListResponse]:
    """
    List all members of an organization.
    
    Requires:
    - JWT authentication
    - Organization membership
    
    Returns members sorted by joined date (ascending).
    """
    service = MembershipService(db)
    memberships = await service.list_members(current_user.id, org_id)
    
    # Convert to response format with user email
    response = []
    for membership in memberships:
        response.append(
            MemberListResponse(
                membership_id=membership.id,
                user_id=membership.user_id,
                email=membership.user.email,
                role=membership.role,
                created_at=membership.user.created_at,  # Using user created_at as proxy
            )
        )
    
    return response


@router.patch(
    "/{org_id}/members/{membership_id}/role",
    response_model=RoleChangeResponse,
    status_code=status.HTTP_200_OK,
)
async def change_member_role(
    org_id: UUID,
    membership_id: UUID,
    data: RoleChangeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RoleChangeResponse:
    """
    Change a member's role.
    
    Rules:
    - Only organization owner can change roles
    - Cannot assign owner role directly (use transfer-ownership)
    - Cannot modify organization owner role
    - Valid roles: admin, member
    
    Returns 400 for invalid requests, 403 for insufficient permissions.
    """
    service = MembershipService(db)
    updated_membership = await service.change_role(
        requester_user_id=current_user.id,
        organization_id=org_id,
        membership_id=membership_id,
        new_role=data.role,
    )
    
    return RoleChangeResponse(
        membership_id=updated_membership.id,
        user_id=updated_membership.user_id,
        new_role=updated_membership.role,
    )


@router.delete(
    "/{org_id}/members/{membership_id}",
    response_model=MemberRemoveResponse,
    status_code=status.HTTP_200_OK,
)
async def remove_member(
    org_id: UUID,
    membership_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MemberRemoveResponse:
    """
    Remove a member from the organization.
    
    Rules:
    - Only organization owner can remove members
    - Cannot remove organization owner
    - Cannot remove yourself
    
    Returns 403 for insufficient permissions.
    """
    service = MembershipService(db)
    await service.remove_member(
        requester_user_id=current_user.id,
        organization_id=org_id,
        membership_id=membership_id,
    )
    
    return MemberRemoveResponse(message="member removed")


@router.post(
    "/{org_id}/transfer-ownership",
    response_model=OwnershipTransferResponse,
    status_code=status.HTTP_200_OK,
)
@router.post(
    "/{org_id}/transfer_ownership",
    response_model=OwnershipTransferResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def transfer_ownership(
    org_id: UUID,
    data: OwnershipTransferRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OwnershipTransferResponse:
    """
    Transfer organization ownership to another member.
    
    Rules:
    - Only current owner can transfer ownership
    - Target must be a member of the organization
    - Target cannot already be owner
    - Cannot transfer to yourself
    
    Behavior:
    - Current owner becomes admin
    - Target becomes owner
    - Transactional (rollback on failure)
    
    Returns 400 for invalid requests, 403 for insufficient permissions.
    """
    service = MembershipService(db)
    await service.transfer_ownership(
        requester_user_id=current_user.id,
        organization_id=org_id,
        new_owner_membership_id=data.new_owner_membership_id,
        new_owner_user_id=data.new_owner_user_id,
    )
    
    return OwnershipTransferResponse(message="ownership transferred")
