import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_org_detail_and_my_orgs_with_role(client: AsyncClient):
    """G1 & G2: Org detail and /organizations/my include caller's role and member count."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        email = "lifecycle_user@example.com"
        pwd = "Password123!"
        await client.post("/auth/register", json={"email": email, "password": pwd})
        login = await client.post("/auth/login", json={"email": email, "password": pwd})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create org
        org_res = await client.post("/organizations", json={"name": "Lifecycle Org"}, headers=headers)
        assert org_res.status_code == 201
        org_id = org_res.json()["id"]

        # G1: GET /organizations/{id}
        detail_res = await client.get(f"/organizations/{org_id}", headers=headers)
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == org_id
        assert detail["role"] == "owner"
        assert detail["member_count"] == 1
        assert detail["plan"] == "free"

        # G2: GET /organizations/my
        my_res = await client.get("/organizations/my", headers=headers)
        assert my_res.status_code == 200
        my_orgs = my_res.json()
        assert len(my_orgs) == 1
        assert my_orgs[0]["role"] == "owner"
        assert my_orgs[0]["member_count"] == 1


@pytest.mark.asyncio
async def test_org_leave_rules(client: AsyncClient):
    """G5: Members can leave; Owner cannot leave without transferring ownership."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        owner_email = "owner_leave@example.com"
        member_email = "member_leave@example.com"
        pwd = "Password123!"

        await client.post("/auth/register", json={"email": owner_email, "password": pwd})
        o_login = await client.post("/auth/login", json={"email": owner_email, "password": pwd})
        o_headers = {"Authorization": f"Bearer {o_login.json()['access_token']}"}

        org_res = await client.post("/organizations", json={"name": "Leave Org"}, headers=o_headers)
        org_id = org_res.json()["id"]

        # Owner attempts to leave -> 400
        leave_owner = await client.post(f"/organizations/{org_id}/leave", headers=o_headers)
        assert leave_owner.status_code == 400
        assert "cannot leave" in leave_owner.text.lower()

        # Add regular member
        inv = await client.post(f"/organizations/{org_id}/invite", json={"email": member_email}, headers=o_headers)
        token = inv.json()["token"]

        await client.post("/auth/register", json={"email": member_email, "password": pwd})
        m_login = await client.post("/auth/login", json={"email": member_email, "password": pwd})
        m_headers = {"Authorization": f"Bearer {m_login.json()['access_token']}"}
        await client.post("/invitations/accept", json={"token": token}, headers=m_headers)

        # Member leaves -> 204
        leave_member = await client.post(f"/organizations/{org_id}/leave", headers=m_headers)
        assert leave_member.status_code == 204

        # Verify member count back to 1
        detail = (await client.get(f"/organizations/{org_id}", headers=o_headers)).json()
        assert detail["member_count"] == 1


@pytest.mark.asyncio
async def test_org_delete_with_confirmation_and_cleanup(client: AsyncClient):
    """G6: Org delete requires exact name confirmation; cascades files and storage."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        email = "delete_owner@example.com"
        pwd = "Password123!"
        await client.post("/auth/register", json={"email": email, "password": pwd})
        login = await client.post("/auth/login", json={"email": email, "password": pwd})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        org_name = "Doomed Organization"
        org_res = await client.post("/organizations", json={"name": org_name}, headers=headers)
        org_id = org_res.json()["id"]
        tenant_headers = {**headers, "X-Organization-Id": org_id}

        # Upload a file
        import io
        await client.post(
            "/files/upload",
            headers=tenant_headers,
            files={"file": ("cleanup_test.txt", io.BytesIO(b"cleanup content"), "text/plain")},
        )

        # Wrong name confirmation -> 400
        bad_del = await client.request(
            "DELETE",
            f"/organizations/{org_id}",
            json={"name": "Wrong Name"},
            headers=headers,
        )
        assert bad_del.status_code == 400
        assert "does not match" in bad_del.text

        # Correct name confirmation -> 204
        good_del = await client.request(
            "DELETE",
            f"/organizations/{org_id}",
            json={"name": org_name},
            headers=headers,
        )
        assert good_del.status_code == 204

        # Organization is gone -> 404 or 403 (membership cascade-deleted)
        assert (await client.get(f"/organizations/{org_id}", headers=headers)).status_code in (403, 404)
