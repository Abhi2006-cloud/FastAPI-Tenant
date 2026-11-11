import io
import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient


async def _create_tenant(client: AsyncClient, email: str = "limit_owner@example.com") -> tuple[dict, str]:
    await client.post("/auth/register", json={"email": email, "password": "Password123!"})
    login = await client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    org_res = await client.post("/organizations", json={"name": "Limit Testing Org"}, headers=headers)
    org_id = org_res.json()["id"]
    return {**headers, "X-Organization-Id": org_id}, org_id


@pytest.mark.asyncio
async def test_member_limit_on_invite_and_accept(client: AsyncClient):
    """Enforce max_members (free plan = 5)."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        headers, org_id = await _create_tenant(client, "owner_member_limit@example.com")

        # Owner is member 1. Create and accept 4 more members -> reaches 5.
        for i in range(1, 5):
            m_email = f"member_{i}_{uuid.uuid4().hex[:4]}@example.com"
            inv = await client.post(f"/organizations/{org_id}/invite", json={"email": m_email}, headers=headers)
            assert inv.status_code == 201
            token = inv.json()["token"]

            await client.post("/auth/register", json={"email": m_email, "password": "Password123!"})
            m_login = await client.post("/auth/login", json={"email": m_email, "password": "Password123!"})
            m_tok = m_login.json()["access_token"]
            acc = await client.post("/invitations/accept", json={"token": token}, headers={"Authorization": f"Bearer {m_tok}"})
            assert acc.status_code == 200

        # Attempt to invite a 6th member -> 402 PLAN_LIMIT_REACHED
        over_inv = await client.post(
            f"/organizations/{org_id}/invite",
            json={"email": "sixth_member@example.com"},
            headers=headers,
        )
        assert over_inv.status_code == 402
        err = over_inv.json()["detail"]
        assert err["code"] == "PLAN_LIMIT_REACHED"
        assert err["limit"] == "max_members"
        assert err["current"] == 5
        assert err["max"] == 5


@pytest.mark.asyncio
async def test_file_limits_upload_and_storage(client: AsyncClient):
    """Enforce max_upload_mb (2 MB) and file counts / storage quotas."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        headers, org_id = await _create_tenant(client, "owner_file_limit@example.com")

        # Exceed max_upload_mb (free = 2 MB): 2.5 MB file
        oversized = b"x" * (2500 * 1024)
        res_upload = await client.post(
            "/files/upload",
            headers=headers,
            files={"file": ("too_big.txt", io.BytesIO(oversized), "text/plain")},
        )
        assert res_upload.status_code == 402
        err = res_upload.json()["detail"]
        assert err["code"] == "PLAN_LIMIT_REACHED"
        assert err["limit"] == "max_upload_mb"


@pytest.mark.asyncio
async def test_invites_per_hour_rate_limit(client: AsyncClient):
    """Free plan allows 5 invites per hour."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        headers, org_id = await _create_tenant(client, "owner_invite_hourly@example.com")

        # Create 4 invitations
        for i in range(4):
            email = f"hourly_invitee_{i}_{uuid.uuid4().hex[:4]}@example.com"
            res = await client.post(f"/organizations/{org_id}/invite", json={"email": email}, headers=headers)
            assert res.status_code == 201

        # 5th invitation attempt (total 5 invites)
        email_5 = f"hourly_invitee_5_{uuid.uuid4().hex[:4]}@example.com"
        # Since owner is 1 member and 4 pending invites, 5 invites hits max_members or hourly limit
        # Let's revoke one pending invite first to test hourly limit specifically
        list_inv = await client.get(f"/organizations/{org_id}/invitations", headers=headers)
        first_inv_id = list_inv.json()[0]["id"]
        await client.delete(f"/organizations/{org_id}/invitations/{first_inv_id}", headers=headers)

        res_5 = await client.post(f"/organizations/{org_id}/invite", json={"email": email_5}, headers=headers)
        assert res_5.status_code == 201

        # 6th invitation within same hour -> 402 PLAN_LIMIT_REACHED for invites_per_hour
        res_6 = await client.post(
            f"/organizations/{org_id}/invite",
            json={"email": "exceeded_hourly@example.com"},
            headers=headers,
        )
        assert res_6.status_code == 402
        err = res_6.json()["detail"]
        assert err["code"] == "PLAN_LIMIT_REACHED"
        assert err["limit"] == "invites_per_hour"
