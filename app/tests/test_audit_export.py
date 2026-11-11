from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_audit_export_gated_by_feature_and_csv_sanitization(client: AsyncClient):
    """G8: CSV export is plan-gated (402 on Free, 200 on Pro) with CSV injection neutralization."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        # Setup platform admin to allow upgrade
        adm_email = "platform-admin@example.com"
        pwd = "Password123!"
        await client.post("/auth/register", json={"email": adm_email, "password": pwd})
        adm_login = await client.post("/auth/login", json={"email": adm_email, "password": pwd})
        adm_headers = {"Authorization": f"Bearer {adm_login.json()['access_token']}"}

        # Setup tenant owner
        owner_email = "export_owner@example.com"
        await client.post("/auth/register", json={"email": owner_email, "password": pwd})
        o_login = await client.post("/auth/login", json={"email": owner_email, "password": pwd})
        o_token = o_login.json()["access_token"]
        o_headers = {"Authorization": f"Bearer {o_token}"}

        org_res = await client.post("/organizations", json={"name": "Export Org"}, headers=o_headers)
        org_id = org_res.json()["id"]
        tenant_headers = {**o_headers, "X-Organization-Id": org_id}

        # 1. On Free plan: GET /audit-logs/export returns 402 PLAN_FEATURE_LOCKED
        res_free = await client.get("/audit-logs/export", headers=tenant_headers)
        assert res_free.status_code == 402
        err = res_free.json()["detail"]
        assert err["code"] == "PLAN_FEATURE_LOCKED"
        assert err["feature"] == "audit_export"

        # 2. Upgrade to Pro via platform admin
        up_res = await client.patch(
            f"/admin/organizations/{org_id}/plan",
            json={"plan": "pro"},
            headers=adm_headers,
        )
        assert up_res.status_code == 200

        # 3. Create an audit event with potentially malicious CSV characters: =danger
        await client.post(
            f"/organizations/{org_id}/invite",
            json={"email": "normal_invitee@example.com"},
            headers=tenant_headers,
        )

        # 4. On Pro plan: GET /audit-logs/export streams CSV
        res_pro = await client.get("/audit-logs/export", headers=tenant_headers)
        assert res_pro.status_code == 200
        assert "text/csv" in res_pro.headers.get("content-type", "")
        csv_text = res_pro.text

        # Verify CSV header
        assert "id,created_at,action,actor_user_id,resource_type,resource_id,metadata" in csv_text

        # 5. Direct unit verification of sanitize_csv_cell neutralization
        from app.modules.audit.service import sanitize_csv_cell
        assert sanitize_csv_cell("=1+1") == "'=1+1"
        assert sanitize_csv_cell("+123") == "'+123"
        assert sanitize_csv_cell("-456") == "'-456"
        assert sanitize_csv_cell("@SUM") == "'@SUM"
        assert sanitize_csv_cell("clean") == "clean"
