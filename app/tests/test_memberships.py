"""
Tests for membership management endpoints (v1.3.0).

Tests cover:
- List organization members
- Change member role
- Remove member
- Transfer ownership
- Permission checks
- Cross-tenant access prevention
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def mock_job_service_enqueue():
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        yield


async def _register_and_token(client: AsyncClient, email: str) -> str:
    """Helper to register a user and return their JWT token."""
    res_reg = await client.post(
        "/auth/register",
        json={"email": email, "password": "securepass123"},
    )
    login = await client.post(
        "/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    data = login.json()
    if "access_token" not in data:
        raise KeyError(
            f"access_token missing for {email}. Register status: {res_reg.status_code} ({res_reg.text}), "
            f"Login status: {login.status_code} ({login.text})"
        )
    return data["access_token"]


async def _create_org_and_get_id(client: AsyncClient, token: str) -> str:
    """Helper to create an organization and return its ID."""
    response = await client.post(
        "/organizations",
        json={"name": "Test Workspace"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()["id"]


async def _add_member_to_org(
    client: AsyncClient,
    org_id: str,
    invitee_email: str,
    inviter_token: str,
) -> str:
    """Helper to invite a member and return the invitation token."""
    response = await client.post(
        f"/organizations/{org_id}/invite",
        json={"email": invitee_email},
        headers={"Authorization": f"Bearer {inviter_token}"},
    )
    return response.json()["token"]


async def _accept_invitation(client: AsyncClient, token: str, invite_token: str) -> None:
    """Helper to accept an invitation."""
    await client.post(
        "/invitations/accept",
        json={"token": invite_token},
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.mark.asyncio
async def test_list_members_as_owner(client: AsyncClient) -> None:
    """Test that organization owner can list all members."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Invite and add a member
    invite_token = await _add_member_to_org(client, org_id, "member@example.com", owner_token)
    member_token = await _register_and_token(client, "member@example.com")
    await _accept_invitation(client, member_token, invite_token)
    
    # List members as owner
    response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    assert response.status_code == 200
    members = response.json()
    assert len(members) == 2
    emails = {m["email"] for m in members}
    assert "owner@example.com" in emails
    assert "member@example.com" in emails


@pytest.mark.asyncio
async def test_list_members_as_member(client: AsyncClient) -> None:
    """Test that regular members can list organization members."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Invite and add a member
    invite_token = await _add_member_to_org(client, org_id, "member@example.com", owner_token)
    member_token = await _register_and_token(client, "member@example.com")
    await _accept_invitation(client, member_token, invite_token)
    
    # List members as regular member
    response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    
    assert response.status_code == 200
    members = response.json()
    assert len(members) == 2


@pytest.mark.asyncio
async def test_list_members_non_member_forbidden(client: AsyncClient) -> None:
    """Test that non-members cannot list organization members."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Try to list as non-member
    non_member_token = await _register_and_token(client, "outsider@example.com")
    response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {non_member_token}"},
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_change_role_as_owner_promote_to_admin(client: AsyncClient) -> None:
    """Test that owner can promote member to admin."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Add a member
    invite_token = await _add_member_to_org(client, org_id, "member@example.com", owner_token)
    member_token = await _register_and_token(client, "member@example.com")
    await _accept_invitation(client, member_token, invite_token)
    
    # Get membership ID
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    member_membership = [m for m in members_response.json() if m["email"] == "member@example.com"][0]
    
    # Promote to admin
    response = await client.patch(
        f"/organizations/{org_id}/members/{member_membership['membership_id']}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    assert response.status_code == 200
    assert response.json()["new_role"] == "admin"


@pytest.mark.asyncio
async def test_change_role_as_owner_demote_to_member(client: AsyncClient) -> None:
    """Test that owner can demote admin to member."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Add an admin
    invite_token = await _add_member_to_org(client, org_id, "admin@example.com", owner_token)
    admin_token = await _register_and_token(client, "admin@example.com")
    await _accept_invitation(client, admin_token, invite_token)
    
    # Get membership ID and promote to admin first
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    admin_membership = [m for m in members_response.json() if m["email"] == "admin@example.com"][0]
    
    await client.patch(
        f"/organizations/{org_id}/members/{admin_membership['membership_id']}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    # Demote back to member
    response = await client.patch(
        f"/organizations/{org_id}/members/{admin_membership['membership_id']}/role",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    assert response.status_code == 200
    assert response.json()["new_role"] == "member"


@pytest.mark.asyncio
async def test_change_role_admin_forbidden(client: AsyncClient) -> None:
    """Test that admin cannot change roles."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Add an admin
    invite_token = await _add_member_to_org(client, org_id, "admin@example.com", owner_token)
    admin_token = await _register_and_token(client, "admin@example.com")
    await _accept_invitation(client, admin_token, invite_token)
    
    # Get membership IDs
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    admin_membership = [m for m in members_response.json() if m["email"] == "admin@example.com"][0]
    owner_membership = [m for m in members_response.json() if m["email"] == "owner@example.com"][0]
    
    # Promote admin to admin role first
    await client.patch(
        f"/organizations/{org_id}/members/{admin_membership['membership_id']}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    # Try to change role as admin
    response = await client.patch(
        f"/organizations/{org_id}/members/{owner_membership['membership_id']}/role",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_change_role_member_forbidden(client: AsyncClient) -> None:
    """Test that regular member cannot change roles."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Add a member
    invite_token = await _add_member_to_org(client, org_id, "member@example.com", owner_token)
    member_token = await _register_and_token(client, "member@example.com")
    await _accept_invitation(client, member_token, invite_token)
    
    # Get membership IDs
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    owner_membership = [m for m in members_response.json() if m["email"] == "owner@example.com"][0]
    
    # Try to change role as member
    response = await client.patch(
        f"/organizations/{org_id}/members/{owner_membership['membership_id']}/role",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_change_role_invalid_role(client: AsyncClient) -> None:
    """Test that invalid role returns 400."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Add a member
    invite_token = await _add_member_to_org(client, org_id, "member@example.com", owner_token)
    member_token = await _register_and_token(client, "member@example.com")
    await _accept_invitation(client, member_token, invite_token)
    
    # Get membership ID
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    member_membership = [m for m in members_response.json() if m["email"] == "member@example.com"][0]
    
    # Try to assign owner role directly
    response = await client.patch(
        f"/organizations/{org_id}/members/{member_membership['membership_id']}/role",
        json={"role": "owner"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_change_role_owner_forbidden(client: AsyncClient) -> None:
    """Test that owner role cannot be modified."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Get owner membership ID
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    owner_membership = [m for m in members_response.json() if m["email"] == "owner@example.com"][0]
    
    # Try to modify owner role
    response = await client.patch(
        f"/organizations/{org_id}/members/{owner_membership['membership_id']}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_remove_member_as_owner(client: AsyncClient) -> None:
    """Test that owner can remove members."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Add a member
    invite_token = await _add_member_to_org(client, org_id, "member@example.com", owner_token)
    member_token = await _register_and_token(client, "member@example.com")
    await _accept_invitation(client, member_token, invite_token)
    
    # Get membership ID
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    member_membership = [m for m in members_response.json() if m["email"] == "member@example.com"][0]
    
    # Remove member
    response = await client.delete(
        f"/organizations/{org_id}/members/{member_membership['membership_id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "member removed"
    
    # Verify member is removed
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert len(members_response.json()) == 1


@pytest.mark.asyncio
async def test_remove_member_admin_forbidden(client: AsyncClient) -> None:
    """Test that admin cannot remove members."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Add admin and member
    admin_invite = await _add_member_to_org(client, org_id, "admin@example.com", owner_token)
    member_invite = await _add_member_to_org(client, org_id, "member@example.com", owner_token)
    
    admin_token = await _register_and_token(client, "admin@example.com")
    await _accept_invitation(client, admin_token, admin_invite)
    
    member_token = await _register_and_token(client, "member@example.com")
    await _accept_invitation(client, member_token, member_invite)
    
    # Promote admin
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    admin_membership = [m for m in members_response.json() if m["email"] == "admin@example.com"][0]
    member_membership = [m for m in members_response.json() if m["email"] == "member@example.com"][0]
    
    await client.patch(
        f"/organizations/{org_id}/members/{admin_membership['membership_id']}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    # Try to remove member as admin
    response = await client.delete(
        f"/organizations/{org_id}/members/{member_membership['membership_id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_remove_member_member_forbidden(client: AsyncClient) -> None:
    """Test that member cannot remove members."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Add members
    invite1 = await _add_member_to_org(client, org_id, "member1@example.com", owner_token)
    invite2 = await _add_member_to_org(client, org_id, "member2@example.com", owner_token)
    
    member1_token = await _register_and_token(client, "member1@example.com")
    await _accept_invitation(client, member1_token, invite1)
    
    member2_token = await _register_and_token(client, "member2@example.com")
    await _accept_invitation(client, member2_token, invite2)
    
    # Get membership IDs
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    member2_membership = [m for m in members_response.json() if m["email"] == "member2@example.com"][0]
    
    # Try to remove as member
    response = await client.delete(
        f"/organizations/{org_id}/members/{member2_membership['membership_id']}",
        headers={"Authorization": f"Bearer {member1_token}"},
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_remove_owner_forbidden(client: AsyncClient) -> None:
    """Test that owner cannot be removed."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Get owner membership ID
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    owner_membership = [m for m in members_response.json() if m["email"] == "owner@example.com"][0]
    
    # Try to remove owner
    response = await client.delete(
        f"/organizations/{org_id}/members/{owner_membership['membership_id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_remove_self_forbidden(client: AsyncClient) -> None:
    """Test that owner cannot remove themselves."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Add a member
    invite_token = await _add_member_to_org(client, org_id, "member@example.com", owner_token)
    member_token = await _register_and_token(client, "member@example.com")
    await _accept_invitation(client, member_token, invite_token)
    
    # Get membership ID
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    member_membership = [m for m in members_response.json() if m["email"] == "member@example.com"][0]
    
    # Try to remove self
    response = await client.delete(
        f"/organizations/{org_id}/members/{member_membership['membership_id']}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_transfer_ownership_success(client: AsyncClient) -> None:
    """Test successful ownership transfer."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Add a member
    invite_token = await _add_member_to_org(client, org_id, "member@example.com", owner_token)
    member_token = await _register_and_token(client, "member@example.com")
    await _accept_invitation(client, member_token, invite_token)
    
    # Get membership IDs
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    member_membership = [m for m in members_response.json() if m["email"] == "member@example.com"][0]
    owner_membership = [m for m in members_response.json() if m["email"] == "owner@example.com"][0]
    
    # Transfer ownership
    response = await client.post(
        f"/organizations/{org_id}/transfer-ownership",
        json={"new_owner_membership_id": member_membership["membership_id"]},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "ownership transferred"
    
    # Verify roles changed
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    members = members_response.json()
    
    new_owner = [m for m in members if m["email"] == "member@example.com"][0]
    old_owner = [m for m in members if m["email"] == "owner@example.com"][0]
    
    assert new_owner["role"] == "owner"
    assert old_owner["role"] == "admin"


@pytest.mark.asyncio
async def test_transfer_ownership_non_owner_forbidden(client: AsyncClient) -> None:
    """Test that non-owner cannot transfer ownership."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Add a member
    invite_token = await _add_member_to_org(client, org_id, "member@example.com", owner_token)
    member_token = await _register_and_token(client, "member@example.com")
    await _accept_invitation(client, member_token, invite_token)
    
    # Get membership IDs
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    owner_membership = [m for m in members_response.json() if m["email"] == "owner@example.com"][0]
    
    # Try to transfer as member
    response = await client.post(
        f"/organizations/{org_id}/transfer-ownership",
        json={"new_owner_membership_id": owner_membership["membership_id"]},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_transfer_ownership_to_self_forbidden(client: AsyncClient) -> None:
    """Test that owner cannot transfer to themselves."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)
    
    # Get owner membership ID
    members_response = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    owner_membership = [m for m in members_response.json() if m["email"] == "owner@example.com"][0]
    
    # Try to transfer to self
    response = await client.post(
        f"/organizations/{org_id}/transfer-ownership",
        json={"new_owner_membership_id": owner_membership["membership_id"]},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_transfer_ownership_cross_tenant_forbidden(client: AsyncClient) -> None:
    """Test that ownership cannot be transferred to member of another org."""
    owner_token = await _register_and_token(client, "owner@example.com")
    org1_id = await _create_org_and_get_id(client, owner_token)
    
    # Create another org and member
    other_owner_token = await _register_and_token(client, "otherowner@example.com")
    org2_id = await _create_org_and_get_id(client, other_owner_token)
    
    other_invite = await _add_member_to_org(client, org2_id, "member@example.com", other_owner_token)
    member_token = await _register_and_token(client, "member@example.com")
    await _accept_invitation(client, member_token, other_invite)
    
    # Get membership ID from other org
    members_response = await client.get(
        f"/organizations/{org2_id}/members",
        headers={"Authorization": f"Bearer {other_owner_token}"},
    )
    member_membership = [m for m in members_response.json() if m["email"] == "member@example.com"][0]
    
    # Try to transfer ownership to member of other org
    response = await client.post(
        f"/organizations/{org1_id}/transfer-ownership",
        json={"new_owner_membership_id": member_membership["membership_id"]},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    
    assert response.status_code == 403
