"""Memberships API client for member management."""

from typing import Any

from frontend.api.client import api_client, APIError


def list_members(organization_id: str) -> list[dict[str, Any]]:
    """
    List all members of an organization.
    
    Args:
        organization_id: UUID of the organization
        
    Returns:
        List of member dictionaries with membership_id, user_id, email, role, created_at
        
    Raises:
        APIError: If the request fails
    """
    return api_client.get(f"/organizations/{organization_id}/members")


def change_member_role(
    organization_id: str, 
    membership_id: str, 
    new_role: str
) -> dict[str, Any]:
    """
    Change a member's role.
    
    Args:
        organization_id: UUID of the organization
        membership_id: UUID of the membership to modify
        new_role: New role ('admin' or 'member')
        
    Returns:
        Response with membership_id, user_id, and new_role
        
    Raises:
        APIError: If the request fails or permissions are insufficient
    """
    return api_client.patch(
        f"/organizations/{organization_id}/members/{membership_id}/role",
        data={"role": new_role}
    )


def remove_member(organization_id: str, membership_id: str) -> dict[str, Any]:
    """
    Remove a member from the organization.
    
    Args:
        organization_id: UUID of the organization
        membership_id: UUID of the membership to remove
        
    Returns:
        Response with success message
        
    Raises:
        APIError: If the request fails or permissions are insufficient
    """
    return api_client.delete(f"/organizations/{organization_id}/members/{membership_id}")


def transfer_ownership(
    organization_id: str, 
    new_owner_membership_id: str
) -> dict[str, Any]:
    """
    Transfer organization ownership to another member.
    
    Args:
        organization_id: UUID of the organization
        new_owner_membership_id: UUID of the membership to transfer ownership to
        
    Returns:
        Response with success message
        
    Raises:
        APIError: If the request fails or permissions are insufficient
    """
    return api_client.post(
        f"/organizations/{organization_id}/transfer-ownership",
        data={"new_owner_membership_id": new_owner_membership_id}
    )
