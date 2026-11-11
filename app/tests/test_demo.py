from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_demo_session_creation_fixtures_and_limits(client: AsyncClient):
    """POST /demo/session creates a real ephemeral demo workspace with populated fixtures."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        res = await client.post("/demo/session")
        assert res.status_code == 201
        data = res.json()

        assert "access_token" in data
        assert "organization_id" in data
        assert "session_id" in data
        assert "expires_in" in data

        org_id = data["organization_id"]
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

        # Verify populated members fixture
        mem_res = await client.get(f"/organizations/{org_id}/members", headers=headers)
        assert mem_res.status_code == 200
        members = mem_res.json()
        assert len(members) >= 2  # Owner + sample members

        # Verify populated files fixture
        file_res = await client.get("/files", headers=headers)
        assert file_res.status_code == 200
        files = file_res.json()
        assert len(files) >= 1

        # Verify audit logs fixture exists
        audit_res = await client.get("/audit-logs", headers=headers)
        assert audit_res.status_code == 200
        logs = audit_res.json()["items"]
        assert len(logs) >= 1

        # Verify demo organization plan is free with standard limits
        ent_res = await client.get(f"/organizations/{org_id}/entitlements", headers=headers)
        assert ent_res.status_code == 200
        ent = ent_res.json()
        assert ent["plan"] == "free"
        assert ent["limits"]["max_members"] == 5


@pytest.mark.asyncio
async def test_demo_upgrade_toggle(client: AsyncClient):
    """POST /demo/upgrade switches the demo workspace to pro plan with pro entitlements."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        sess_res = await client.post("/demo/session")
        assert sess_res.status_code == 201
        sess_data = sess_res.json()

        org_id = sess_data["organization_id"]
        token = sess_data["access_token"]
        headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

        # Toggle upgrade to pro
        up_res = await client.post("/demo/upgrade", headers=headers)
        assert up_res.status_code == 200
        up_data = up_res.json()
        assert up_data["plan"] == "pro"

        # Verify entitlements now show Pro quotas
        ent_res = await client.get(f"/organizations/{org_id}/entitlements", headers=headers)
        assert ent_res.status_code == 200
        ent = ent_res.json()
        assert ent["plan"] == "pro"
        assert ent["limits"]["max_members"] == 50


@pytest.mark.asyncio
async def test_demo_disabled_returns_404(client: AsyncClient, monkeypatch):
    """When DEMO_ENABLED=False, /demo/session and /demo/upgrade return 404."""
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_enabled", False)

    res = await client.post("/demo/session")
    assert res.status_code == 404
    assert "Demo mode is disabled" in res.text


@pytest.mark.asyncio
async def test_demo_session_rate_limit_10_per_hour(client: AsyncClient):
    """POST /demo/session is rate limited to 10/hour/IP."""
    fixed_time = 1700000010.0
    with patch("app.core.rate_limit.time.time", return_value=fixed_time), \
         patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        # First 10 requests allowed
        for i in range(10):
            res = await client.post(
                "/demo/session",
                headers={"X-Forwarded-For": "198.51.100.42"},
            )
            assert res.status_code == 201, f"Failed at request {i+1}: {res.text}"
            assert res.headers.get("X-RateLimit-Limit") == "10"

        # 11th request triggers 429 RATE_LIMITED
        limited_res = await client.post(
            "/demo/session",
            headers={"X-Forwarded-For": "198.51.100.42"},
        )
        assert limited_res.status_code == 429
        assert limited_res.headers.get("X-RateLimit-Remaining") == "0"
        assert "Retry-After" in limited_res.headers
        assert limited_res.headers.get("X-RateLimit-Limit") == "10"
        err = limited_res.json()["detail"]
        assert err["code"] == "RATE_LIMITED"

