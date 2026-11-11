from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_endpoints_require_platform_admin(client: AsyncClient):
    """G9: /email/test and /jobs endpoints strictly require platform admin privilege."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        # Setup regular user
        await client.post("/auth/register", json={"email": "regular_user@example.com", "password": "Password123!"})
        reg_login = await client.post("/auth/login", json={"email": "regular_user@example.com", "password": "Password123!"})
        reg_token = reg_login.json()["access_token"]
        reg_headers = {"Authorization": f"Bearer {reg_token}"}

        org_res = await client.post("/organizations", json={"name": "Isolation Org"}, headers=reg_headers)
        org_id = org_res.json()["id"]
        tenant_headers = {**reg_headers, "X-Organization-Id": org_id}

        # 1. Non-platform-admin POST /email/test -> 403
        res_email = await client.post(
            "/email/test",
            json={"to_email": "test@example.com", "subject": "Test", "template_name": "welcome.html"},
            headers=tenant_headers,
        )
        assert res_email.status_code == 403
        assert "Platform administrator privilege required" in res_email.text

        # 2. Non-platform-admin GET /jobs -> 403
        res_jobs = await client.get("/jobs", headers=tenant_headers)
        assert res_jobs.status_code == 403
        assert "Platform administrator privilege required" in res_jobs.text


@pytest.mark.asyncio
async def test_cross_tenant_email_and_jobs_isolation_under_admin(client: AsyncClient):
    """G9: Even for platform admins, endpoints strictly respect the X-Organization-Id header."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        # Platform admin creates Org A and Org B
        adm_email = "platform-admin@example.com"
        pwd = "Password123!"
        await client.post("/auth/register", json={"email": adm_email, "password": pwd})
        login = await client.post("/auth/login", json={"email": adm_email, "password": pwd})
        token = login.json()["access_token"]
        auth_header = {"Authorization": f"Bearer {token}"}

        org_a = (await client.post("/organizations", json={"name": "Org A"}, headers=auth_header)).json()["id"]
        org_b = (await client.post("/organizations", json={"name": "Org B"}, headers=auth_header)).json()["id"]

        headers_a = {**auth_header, "X-Organization-Id": org_a}
        headers_b = {**auth_header, "X-Organization-Id": org_b}

        # Create email log in Org A
        res_test = await client.post(
            "/email/test",
            json={"to_email": "org_a_secret@example.com", "subject": "Secret A", "template_name": "welcome.html"},
            headers=headers_a,
        )
        assert res_test.status_code == 201

        # Org B email logs should NOT contain Org A's email
        res_logs_b = await client.get("/email/logs", headers=headers_b)
        assert res_logs_b.status_code == 200
        logs_b = res_logs_b.json()["logs"]
        assert not any(l["recipient_email"] == "org_a_secret@example.com" for l in logs_b)

        # Mock job for Org A
        mock_job = MagicMock()
        mock_job.id = "mock-job-a-999"
        mock_job.get_status.return_value = "finished"
        mock_job.origin = "default"
        mock_job.created_at = None
        mock_job.started_at = None
        mock_job.ended_at = None
        mock_job.result = {"status": "ok"}
        mock_job.exc_info = None
        mock_job.meta = {"organization_id": org_a}

        with (
            patch("app.services.job_service.Job.fetch", return_value=mock_job),
            patch("app.services.job_service.get_sync_redis_connection", return_value=MagicMock()),
        ):
            # Fetching from Org B context returns 404 (isolation preserved)
            res_job_b = await client.get(f"/jobs/{mock_job.id}", headers=headers_b)
            assert res_job_b.status_code == 404

            # Fetching from Org A context returns 200
            res_job_a = await client.get(f"/jobs/{mock_job.id}", headers=headers_a)
            assert res_job_a.status_code == 200

