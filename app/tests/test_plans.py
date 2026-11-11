import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_plans_public_listing(client: AsyncClient):
    """GET /plans returns all plans with limits and features without auth."""
    res = await client.get("/plans")
    assert res.status_code == 200
    plans = res.json()
    assert len(plans) >= 3
    plan_ids = [p["id"] for p in plans]
    assert "free" in plan_ids
    assert "pro" in plan_ids
    assert "enterprise" in plan_ids

    free_plan = next(p for p in plans if p["id"] == "free")
    assert free_plan["limits"]["max_members"] == 5
    assert free_plan["limits"]["max_files"] == 20
    assert free_plan["limits"]["org_storage_mb"] == 25
    assert any(f["key"] == "audit_export" for f in free_plan["features"])


@pytest.mark.asyncio
async def test_organization_entitlements_and_upgrade_request(client: AsyncClient):
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        # Register user and create org
        reg = await client.post("/auth/register", json={"email": "planowner@example.com", "password": "Password123!"})
        login = await client.post("/auth/login", json={"email": "planowner@example.com", "password": "Password123!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        org_res = await client.post("/organizations", json={"name": "Entitlements Org"}, headers=headers)
        org_id = org_res.json()["id"]
        tenant_headers = {**headers, "X-Organization-Id": org_id}

        # Check entitlements
        ent_res = await client.get(f"/organizations/{org_id}/entitlements", headers=tenant_headers)
        assert ent_res.status_code == 200
        ent = ent_res.json()
        assert ent["plan"] == "free"
        assert ent["limits"]["max_members"] == 5
        assert ent["usage"]["members_count"] == 1
        assert ent["invites_remaining_this_hour"] == 5

        # Feature state evaluation
        features_dict = {f["key"]: f["state"] for f in ent["features"]}
        assert features_dict["audit_export"] == "plan_locked"  # requires pro, free is locked
        assert features_dict["email_delivery"] == "plan_locked"
        assert features_dict["sso"] == "coming_soon"

        # Submit upgrade request
        up_res = await client.post(
            f"/organizations/{org_id}/upgrade-request",
            json={"requested_plan": "pro", "message": "Need more members and export"},
            headers=tenant_headers,
        )
        assert up_res.status_code == 201
        up_data = up_res.json()
        assert up_data["requested_plan"] == "pro"
        assert up_data["status"] == "pending"


@pytest.mark.asyncio
async def test_admin_upgrade_requests_and_plan_update(client: AsyncClient):
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        # Setup non-admin and platform-admin
        await client.post("/auth/register", json={"email": "regular@example.com", "password": "Password123!"})
        reg_login = await client.post("/auth/login", json={"email": "regular@example.com", "password": "Password123!"})
        reg_token = reg_login.json()["access_token"]
        reg_headers = {"Authorization": f"Bearer {reg_token}"}

        await client.post("/auth/register", json={"email": "platform-admin@example.com", "password": "Password123!"})
        adm_login = await client.post("/auth/login", json={"email": "platform-admin@example.com", "password": "Password123!"})
        adm_token = adm_login.json()["access_token"]
        adm_headers = {"Authorization": f"Bearer {adm_token}"}

        org_res = await client.post("/organizations", json={"name": "Upgrade Test Org"}, headers=reg_headers)
        org_id = org_res.json()["id"]

        # Regular user cannot view admin upgrade requests
        forbidden_req = await client.get("/admin/upgrade-requests", headers=reg_headers)
        assert forbidden_req.status_code == 403

        # Platform admin views upgrade requests
        adm_req = await client.get("/admin/upgrade-requests", headers=adm_headers)
        assert adm_req.status_code == 200

        # Regular user cannot patch organization plan
        forbidden_patch = await client.patch(
            f"/admin/organizations/{org_id}/plan",
            json={"plan": "pro"},
            headers=reg_headers,
        )
        assert forbidden_patch.status_code == 403

        # Platform admin patches organization plan to pro
        patch_res = await client.patch(
            f"/admin/organizations/{org_id}/plan",
            json={"plan": "pro"},
            headers=adm_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["plan"] == "pro"

        # Verify new entitlements reflect pro plan
        tenant_headers = {**reg_headers, "X-Organization-Id": org_id}
        new_ent = await client.get(f"/organizations/{org_id}/entitlements", headers=tenant_headers)
        assert new_ent.status_code == 200
        assert new_ent.json()["plan"] == "pro"
        assert new_ent.json()["limits"]["max_members"] == 50
        pro_features = {f["key"]: f["state"] for f in new_ent.json()["features"]}
        assert pro_features["audit_export"] == "included"
        assert pro_features["email_delivery"] == "deployment_disabled"
