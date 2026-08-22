"""
Tests for audit logs (v1.5.0).

Covers event creation, listing, filtering, search, pagination,
cross-tenant access, and RBAC read access for all member roles.
"""

import io

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def mock_job_service_enqueue():
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        yield


async def _register_and_token(client: AsyncClient, email: str) -> str:
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


async def _create_org(client: AsyncClient, token: str, name: str = "Test Org") -> str:
    response = await client.post(
        "/organizations",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()["id"]


def _tenant_headers(token: str, org_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": org_id,
    }


async def _list_audit_logs(
    client: AsyncClient,
    token: str,
    org_id: str,
    **params,
) -> dict:
    response = await client.get(
        "/audit-logs",
        headers=_tenant_headers(token, org_id),
        params=params,
    )
    return response


@pytest.mark.asyncio
async def test_organization_created_audit_event(client: AsyncClient) -> None:
    token = await _register_and_token(client, "orgcreator@example.com")
    org_id = await _create_org(client, token, "Audit Org")

    response = await _list_audit_logs(client, token, org_id)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    actions = [item["action"] for item in body["items"]]
    assert "ORGANIZATION_CREATED" in actions

    org_event = next(i for i in body["items"] if i["action"] == "ORGANIZATION_CREATED")
    assert org_event["resource_type"] == "organization"
    assert org_event["resource_id"] == org_id
    assert org_event["metadata"]["name"] == "Audit Org"


@pytest.mark.asyncio
async def test_member_invited_audit_event(client: AsyncClient) -> None:
    owner_token = await _register_and_token(client, "inviter@example.com")
    org_id = await _create_org(client, owner_token)

    invite_response = await client.post(
        f"/organizations/{org_id}/invite",
        json={"email": "invitee@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert invite_response.status_code == 201

    response = await _list_audit_logs(client, owner_token, org_id, action="MEMBER_INVITED")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["items"][0]["action"] == "MEMBER_INVITED"
    assert body["items"][0]["metadata"]["email"] == "invitee@example.com"


@pytest.mark.asyncio
async def test_invitation_accepted_audit_event(client: AsyncClient) -> None:
    owner_token = await _register_and_token(client, "owner-inv@example.com")
    org_id = await _create_org(client, owner_token)

    invite = await client.post(
        f"/organizations/{org_id}/invite",
        json={"email": "accepted@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    invite_token = invite.json()["token"]
    member_token = await _register_and_token(client, "accepted@example.com")

    await client.post(
        "/invitations/accept",
        json={"token": invite_token},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    response = await _list_audit_logs(
        client, owner_token, org_id, action="INVITATION_ACCEPTED"
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert response.json()["items"][0]["action"] == "INVITATION_ACCEPTED"


@pytest.mark.asyncio
async def test_member_role_changed_audit_event(client: AsyncClient) -> None:
    owner_token = await _register_and_token(client, "roleowner@example.com")
    org_id = await _create_org(client, owner_token)

    invite = await client.post(
        f"/organizations/{org_id}/invite",
        json={"email": "rolemember@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    member_token = await _register_and_token(client, "rolemember@example.com")
    await client.post(
        "/invitations/accept",
        json={"token": invite.json()["token"]},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    members = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    membership_id = [
        m for m in members.json() if m["email"] == "rolemember@example.com"
    ][0]["membership_id"]

    await client.patch(
        f"/organizations/{org_id}/members/{membership_id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = await _list_audit_logs(
        client, owner_token, org_id, action="MEMBER_ROLE_CHANGED"
    )
    assert response.status_code == 200
    event = response.json()["items"][0]
    assert event["metadata"]["old_role"] == "member"
    assert event["metadata"]["new_role"] == "admin"


@pytest.mark.asyncio
async def test_member_removed_audit_event(client: AsyncClient) -> None:
    owner_token = await _register_and_token(client, "removeowner@example.com")
    org_id = await _create_org(client, owner_token)

    invite = await client.post(
        f"/organizations/{org_id}/invite",
        json={"email": "removemember@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    member_token = await _register_and_token(client, "removemember@example.com")
    await client.post(
        "/invitations/accept",
        json={"token": invite.json()["token"]},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    members = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    membership_id = [
        m for m in members.json() if m["email"] == "removemember@example.com"
    ][0]["membership_id"]

    await client.delete(
        f"/organizations/{org_id}/members/{membership_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = await _list_audit_logs(
        client, owner_token, org_id, action="MEMBER_REMOVED"
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert response.json()["items"][0]["metadata"]["removed_role"] == "member"


@pytest.mark.asyncio
async def test_ownership_transferred_audit_event(client: AsyncClient) -> None:
    owner_token = await _register_and_token(client, "transferowner@example.com")
    org_id = await _create_org(client, owner_token)

    invite = await client.post(
        f"/organizations/{org_id}/invite",
        json={"email": "newowner@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    member_token = await _register_and_token(client, "newowner@example.com")
    await client.post(
        "/invitations/accept",
        json={"token": invite.json()["token"]},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    members = await client.get(
        f"/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    new_owner_membership = [
        m for m in members.json() if m["email"] == "newowner@example.com"
    ][0]["membership_id"]

    await client.post(
        f"/organizations/{org_id}/transfer-ownership",
        json={"new_owner_membership_id": new_owner_membership},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = await _list_audit_logs(
        client, member_token, org_id, action="OWNERSHIP_TRANSFERRED"
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_file_uploaded_audit_event(client: AsyncClient) -> None:
    token = await _register_and_token(client, "fileuploader@example.com")
    org_id = await _create_org(client, token)
    headers = _tenant_headers(token, org_id)

    await client.post(
        "/files/upload",
        headers=headers,
        files={"file": ("audit.txt", io.BytesIO(b"audit content"), "text/plain")},
    )

    response = await _list_audit_logs(client, token, org_id, action="FILE_UPLOADED")
    assert response.status_code == 200
    event = response.json()["items"][0]
    assert event["resource_type"] == "file"
    assert event["metadata"]["file_name"] == "audit.txt"


@pytest.mark.asyncio
async def test_file_downloaded_audit_event(client: AsyncClient) -> None:
    token = await _register_and_token(client, "filedownloader@example.com")
    org_id = await _create_org(client, token)
    headers = _tenant_headers(token, org_id)

    upload = await client.post(
        "/files/upload",
        headers=headers,
        files={"file": ("download-me.txt", io.BytesIO(b"data"), "text/plain")},
    )
    file_id = upload.json()["id"]

    await client.get(f"/files/{file_id}/download", headers=headers)

    response = await _list_audit_logs(client, token, org_id, action="FILE_DOWNLOADED")
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert response.json()["items"][0]["resource_id"] == file_id


@pytest.mark.asyncio
async def test_file_deleted_audit_event(client: AsyncClient) -> None:
    token = await _register_and_token(client, "filedeleter@example.com")
    org_id = await _create_org(client, token)
    headers = _tenant_headers(token, org_id)

    upload = await client.post(
        "/files/upload",
        headers=headers,
        files={"file": ("delete-me.txt", io.BytesIO(b"data"), "text/plain")},
    )
    file_id = upload.json()["id"]

    await client.delete(f"/files/{file_id}", headers=headers)

    response = await _list_audit_logs(client, token, org_id, action="FILE_DELETED")
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert response.json()["items"][0]["metadata"]["file_name"] == "delete-me.txt"


@pytest.mark.asyncio
async def test_list_audit_logs_pagination(client: AsyncClient) -> None:
    token = await _register_and_token(client, "pagination@example.com")
    org_id = await _create_org(client, token)
    headers = _tenant_headers(token, org_id)

    for i in range(3):
        await client.post(
            "/files/upload",
            headers=headers,
            files={"file": (f"file{i}.txt", io.BytesIO(b"x"), "text/plain")},
        )

    response = await _list_audit_logs(client, token, org_id, page=1, page_size=2)
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2
    assert body["total"] >= 4  # org created + 3 uploads

    # Newest first: first item should be most recent upload
    assert body["items"][0]["action"] == "FILE_UPLOADED"


@pytest.mark.asyncio
async def test_filter_audit_logs_by_resource_type(client: AsyncClient) -> None:
    token = await _register_and_token(client, "filtertype@example.com")
    org_id = await _create_org(client, token)
    headers = _tenant_headers(token, org_id)

    await client.post(
        "/files/upload",
        headers=headers,
        files={"file": ("typed.txt", io.BytesIO(b"x"), "text/plain")},
    )

    response = await _list_audit_logs(client, token, org_id, resource_type="file")
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["resource_type"] == "file"


@pytest.mark.asyncio
async def test_filter_audit_logs_by_actor(client: AsyncClient) -> None:
    owner_token = await _register_and_token(client, "actorfilter@example.com")
    org_id = await _create_org(client, owner_token)

    me = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    owner_id = me.json()["id"]

    response = await _list_audit_logs(
        client, owner_token, org_id, actor_user_id=owner_id
    )
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["actor_user_id"] == owner_id


@pytest.mark.asyncio
async def test_search_audit_logs(client: AsyncClient) -> None:
    token = await _register_and_token(client, "searchuser@example.com")
    org_id = await _create_org(client, token)
    headers = _tenant_headers(token, org_id)

    await client.post(
        "/files/upload",
        headers=headers,
        files={"file": ("unique-search-name.txt", io.BytesIO(b"x"), "text/plain")},
    )

    response = await client.get(
        "/audit-logs/search",
        headers=headers,
        params={"q": "unique-search-name"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["query"] == "unique-search-name"


@pytest.mark.asyncio
async def test_search_audit_logs_by_action(client: AsyncClient) -> None:
    token = await _register_and_token(client, "searchaction@example.com")
    org_id = await _create_org(client, token)

    response = await client.get(
        "/audit-logs/search",
        headers=_tenant_headers(token, org_id),
        params={"action": "ORGANIZATION_CREATED"},
    )
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["action"] == "ORGANIZATION_CREATED"


@pytest.mark.asyncio
async def test_audit_logs_cross_tenant_forbidden(client: AsyncClient) -> None:
    owner_token = await _register_and_token(client, "tenantowner@example.com")
    org_id = await _create_org(client, owner_token)

    outsider_token = await _register_and_token(client, "tenantoutsider@example.com")
    await _create_org(client, outsider_token, "Outsider Org")

    response = await _list_audit_logs(client, outsider_token, org_id)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_member_read_access(client: AsyncClient) -> None:
    owner_token = await _register_and_token(client, "readowner@example.com")
    org_id = await _create_org(client, owner_token)

    invite = await client.post(
        f"/organizations/{org_id}/invite",
        json={"email": "readmember@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    member_token = await _register_and_token(client, "readmember@example.com")
    await client.post(
        "/invitations/accept",
        json={"token": invite.json()["token"]},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    response = await _list_audit_logs(client, member_token, org_id)
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_audit_logs_require_organization_header(client: AsyncClient) -> None:
    token = await _register_and_token(client, "noheader@example.com")
    response = await client.get(
        "/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
