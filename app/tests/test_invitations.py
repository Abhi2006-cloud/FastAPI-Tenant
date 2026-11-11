import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient


async def _create_org(client: AsyncClient, email: str = "inv_owner@example.com") -> tuple[dict, str]:
    await client.post("/auth/register", json={"email": email, "password": "Password123!"})
    login = await client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    org_res = await client.post("/organizations", json={"name": "Inv Org"}, headers=headers)
    org_id = org_res.json()["id"]
    return {**headers, "X-Organization-Id": org_id}, org_id


@pytest.mark.asyncio
async def test_invitation_lifecycle(client: AsyncClient):
    """Test create, idempotent resend, list (G3), revoke (G4), and accept."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        headers, org_id = await _create_org(client, "lifecycle_owner@example.com")
        invitee_email = "invitee_1@example.com"

        # 1. Create invitation
        res1 = await client.post(
            f"/organizations/{org_id}/invite",
            json={"email": invitee_email},
            headers=headers,
        )
        assert res1.status_code == 201
        inv1 = res1.json()
        assert inv1["token"] is not None
        assert inv1["delivery_mode"] == "manual"
        token = inv1["token"]

        # 2. Idempotent re-send returns same pending invitation
        res2 = await client.post(
            f"/organizations/{org_id}/invite",
            json={"email": invitee_email},
            headers=headers,
        )
        assert res2.status_code == 201
        inv2 = res2.json()
        assert inv2["token"] == token

        # 3. G3: List invitations (owner/admin)
        res_list = await client.get(f"/organizations/{org_id}/invitations", headers=headers)
        assert res_list.status_code == 200
        invs = res_list.json()
        assert len(invs) == 1
        assert invs[0]["email"] == invitee_email

        # 4. G4: Revoke invitation
        res_revoke = await client.delete(f"/organizations/{org_id}/invitations/{inv1['id']}", headers=headers)
        assert res_revoke.status_code == 200
        assert res_revoke.json()["status"] == "revoked"

        # Attempt to accept revoked invitation -> 400
        await client.post("/auth/register", json={"email": invitee_email, "password": "Password123!"})
        m_login = await client.post("/auth/login", json={"email": invitee_email, "password": "Password123!"})
        m_tok = m_login.json()["access_token"]
        m_headers = {"Authorization": f"Bearer {m_tok}"}

        res_acc = await client.post("/invitations/accept", json={"token": token}, headers=m_headers)
        assert res_acc.status_code == 400
        assert "no longer valid" in res_acc.text


@pytest.mark.asyncio
async def test_invitation_email_mismatch_and_double_accept_guard(client: AsyncClient):
    """Test wrong email rejection and G11 double-accept guard."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        headers, org_id = await _create_org(client, "guard_owner@example.com")
        invitee_email = "target_member@example.com"

        res_invite = await client.post(f"/organizations/{org_id}/invite", json={"email": invitee_email}, headers=headers)
        token = res_invite.json()["token"]

        # Wrong user attempts to accept -> 400
        await client.post("/auth/register", json={"email": "wrong_user@example.com", "password": "Password123!"})
        w_login = await client.post("/auth/login", json={"email": "wrong_user@example.com", "password": "Password123!"})
        w_headers = {"Authorization": f"Bearer {w_login.json()['access_token']}"}

        res_wrong = await client.post("/invitations/accept", json={"token": token}, headers=w_headers)
        assert res_wrong.status_code == 400
        assert "does not match" in res_wrong.text

        # Correct user accepts
        await client.post("/auth/register", json={"email": invitee_email, "password": "Password123!"})
        c_login = await client.post("/auth/login", json={"email": invitee_email, "password": "Password123!"})
        c_headers = {"Authorization": f"Bearer {c_login.json()['access_token']}"}

        res_ok = await client.post("/invitations/accept", json={"token": token}, headers=c_headers)
        assert res_ok.status_code == 200

        # G11: Attempt to accept again -> 409 or 400
        res_double = await client.post("/invitations/accept", json={"token": token}, headers=c_headers)
        assert res_double.status_code in (400, 409)

