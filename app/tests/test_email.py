"""Comprehensive automated tests for Email Infrastructure & Invitation Workflow."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.infrastructure.email.console_provider import ConsoleProvider
from app.infrastructure.email.exceptions import EmailRateLimitException
from app.infrastructure.email.health import check_email_health
from app.infrastructure.email.renderer import email_renderer
from app.infrastructure.email.resend_provider import ResendProvider
from app.infrastructure.email.service import EmailService
from app.jobs.email_tasks import _process_email_job
from app.modules.email.models import EmailStatus
from app.modules.email.repository import EmailLogRepository

pytestmark = pytest.mark.asyncio


async def _register_and_login(client: AsyncClient, email: str = "testuser@example.com") -> str:
    await client.post("/auth/register", json={"email": email, "password": "securepass123"})
    login_res = await client.post("/auth/login", json={"email": email, "password": "securepass123"})
    return login_res.json()["access_token"]


async def _create_organization(client: AsyncClient, token: str, name: str = "Email Test Org") -> str:
    res = await client.post(
        "/organizations",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    return res.json()["id"]


async def test_console_provider_send_email():
    provider = ConsoleProvider()
    assert provider.name == "console"
    assert provider.validate_configuration() is True

    res = await provider.send_email(
        to="test@example.com",
        subject="Test Subject",
        html_content="<h1>Hello</h1><p>World</p>",
        text_content="Hello World",
    )

    assert res["status"] == "sent"
    assert res["provider"] == "console"
    assert res["id"].startswith("console-")


async def test_resend_provider_mocked():
    provider = ResendProvider()
    assert provider.name == "resend"

    settings = get_settings()
    with patch.object(settings, "resend_api_key", "re_mock_key_12345"):
        assert provider.validate_configuration() is True

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"id": "msg_resend_12345"}

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            res = await provider.send_email(
                to="recipient@example.com",
                subject="Resend Subject",
                html_content="<p>Test</p>",
                text_content="Test",
            )
            assert res["status"] == "sent"
            assert res["id"] == "msg_resend_12345"


async def test_template_renderer_html_and_plain_text():
    html, text = email_renderer.render(
        "invitation.html",
        context={
            "organization_name": "Acme Corp",
            "inviter_name": "Alice Admin",
            "join_url": "http://localhost:8501/invitations?token=xyz123",
        },
    )

    assert "Acme Corp" in html
    assert "Alice Admin" in html
    assert "Join Workspace" in html
    assert "Acme Corp" in text
    assert "http://localhost:8501/invitations?token=xyz123" in text


async def test_email_service_queue_and_process_job(db_session):
    service = EmailService(db_session)

    # Mock JobService.enqueue to prevent async loop deadlock in unit tests
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        log = await service.queue_email(
            recipient_email="queue_test@example.com",
            template_name="welcome.html",
            subject="Welcome Queue Test",
            context={"user_name": "Test User"},
        )

        assert log.id is not None
        assert log.status == EmailStatus.QUEUED
        assert log.recipient_email == "queue_test@example.com"

        # Process job via background worker function
        job_res = await _process_email_job(log.id, db_session)
        assert job_res["status"] == "sent"

        # Verify EmailLog was updated to SENT in database
        repo = EmailLogRepository(db_session)
        updated_log = await repo.get_by_id(log.id)
        assert updated_log.status == EmailStatus.SENT
        assert updated_log.sent_at is not None
        assert updated_log.provider_message_id is not None


async def test_email_rate_limiting(db_session):
    import uuid
    service = EmailService(db_session)
    org_id = uuid.uuid4()

    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 25  # Exceeds 20/hr limit

    with patch("app.core.redis.RedisClient.get_client", return_value=mock_redis):
        with pytest.raises(EmailRateLimitException):
            await service.check_rate_limit(org_id)



async def test_invitation_idempotency_and_resend(client: AsyncClient):
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        token = await _register_and_login(client, "idempotent_owner@example.com")
        org_id = await _create_organization(client, token, "Idempotent Org")
        headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

        # Create invitation 1
        res1 = await client.post(
            f"/organizations/{org_id}/invite",
            json={"email": "invitee_user@example.com"},
            headers=headers,
        )
        assert res1.status_code == 201
        data1 = res1.json()
        invite_id_1 = data1["id"]

        # Create invitation 2 with same email (idempotent return)
        res2 = await client.post(
            f"/organizations/{org_id}/invite",
            json={"email": "invitee_user@example.com"},
            headers=headers,
        )
        assert res2.status_code == 201
        data2 = res2.json()
        assert data2["id"] == invite_id_1

        # Resend invitation via endpoint
        res3 = await client.post(
            f"/invitations/{invite_id_1}/resend",
            headers=headers,
        )
        assert res3.status_code == 200
        assert res3.json()["id"] == invite_id_1


async def test_email_health_check():
    health = await check_email_health(force_refresh=True)
    assert "status" in health
    assert health["status"] in ("console", "connected", "misconfigured", "degraded", "development")


async def test_email_api_endpoints(client: AsyncClient):
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        token = await _register_and_login(client, "platform-admin@example.com")
        org_id = await _create_organization(client, token, "Email Admin Org")
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org_id,
        }

        # GET /email/stats
        res_stats = await client.get("/email/stats", headers=headers)
        assert res_stats.status_code == 200
        assert "total_emails" in res_stats.json()

        # POST /email/test
        res_test = await client.post(
            "/email/test",
            json={
                "to_email": "api_test@example.com",
                "subject": "API Test",
                "template_name": "welcome.html",
            },
            headers=headers,
        )
        assert res_test.status_code == 201
        log_id = res_test.json()["id"]
        assert log_id is not None

        # GET /email/logs
        res_logs = await client.get("/email/logs", headers=headers)
        assert res_logs.status_code == 200
        assert res_logs.json()["total"] >= 1

        # GET /health check includes email
        res_health = await client.get("/health")
        assert res_health.status_code == 200
        assert "email" in res_health.json()


async def test_cross_tenant_email_log_isolation(client: AsyncClient):
    """Verify that Tenant B cannot see Tenant A's email logs."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        # Org A creates an email
        token_a = await _register_and_login(client, "platform-admin@example.com")
        org_a_id = await _create_organization(client, token_a, "Org A")
        headers_a = {"Authorization": f"Bearer {token_a}", "X-Organization-Id": org_a_id}

        res_test = await client.post(
            "/email/test",
            json={
                "to_email": "confidential_a@example.com",
                "subject": "Confidential Org A Email",
                "template_name": "welcome.html",
            },
            headers=headers_a,
        )
        assert res_test.status_code == 201
        log_a_id = res_test.json()["id"]

        # Org B checks their email logs
        token_b = await _register_and_login(client, "owner_b@example.com")
        org_b_id = await _create_organization(client, token_b, "Org B")
        headers_b = {"Authorization": f"Bearer {token_b}", "X-Organization-Id": org_b_id}

        res_logs_b = await client.get("/email/logs", headers=headers_b)
        assert res_logs_b.status_code == 200
        logs_b = res_logs_b.json()["logs"]
        recipients_b = [l["recipient_email"] for l in logs_b]
        assert "confidential_a@example.com" not in recipients_b

        # Org B attempts to retry Org A's email log -> 404 (ownership check)
        res_retry = await client.post(f"/email/logs/{log_a_id}/retry", headers=headers_b)
        assert res_retry.status_code == 404


async def test_email_test_endpoint_production_mode_disabled(client: AsyncClient):
    """Verify that in production mode, /email/test is disabled with 403."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        token = await _register_and_login(client, "platform-admin@example.com")
        org_id = await _create_organization(client, token, "Prod Org")
        headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}
        settings = get_settings()

        with (
            patch.object(settings, "environment", "production"),
            patch.object(settings, "email_mode", "production"),
        ):
            res_test = await client.post(
                "/email/test",
                json={
                    "to_email": "spam_target@example.com",
                    "subject": "Test",
                    "template_name": "welcome.html",
                },
                headers=headers,
            )
            assert res_test.status_code == 403
            assert "disabled in production" in res_test.text


async def test_email_endpoints_require_owner_or_admin_role(client: AsyncClient):
    """Verify that regular members cannot list email logs or send test emails."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        owner_token = await _register_and_login(client, "owner_email_perm@example.com")
        org_id = await _create_organization(client, owner_token, "Perm Org")
        owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Organization-Id": org_id}

        # Add member
        invite_res = await client.post(
            f"/organizations/{org_id}/invite",
            json={"email": "member_email_perm@example.com"},
            headers=owner_headers,
        )
        invite_token = invite_res.json()["token"]

        member_token = await _register_and_login(client, "member_email_perm@example.com")
        await client.post(
            "/invitations/accept",
            json={"token": invite_token},
            headers={"Authorization": f"Bearer {member_token}"},
        )

        member_headers = {"Authorization": f"Bearer {member_token}", "X-Organization-Id": org_id}

        # Member attempts to get stats -> 403
        res_stats = await client.get("/email/stats", headers=member_headers)
        assert res_stats.status_code == 403
        assert "Insufficient permissions" in res_stats.text

        # Member attempts to list logs -> 403
        res_logs = await client.get("/email/logs", headers=member_headers)
        assert res_logs.status_code == 403

        # Member attempts to send test email -> 403
        res_test = await client.post(
            "/email/test",
            json={"to_email": "target@example.com", "subject": "Test", "template_name": "welcome.html"},
            headers=member_headers,
        )
        assert res_test.status_code == 403


async def test_development_mode_invitation_fallback(client: AsyncClient):
    """Verify that in Development Mode, creating invitations returns token, invitation_url, and manual_sharing_required status."""
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        token = await _register_and_login(client, "dev_owner@example.com")
        org_id = await _create_organization(client, token, "Dev Mode Org")
        headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}
        settings = get_settings()

        # Create Invitation in Development Mode
        with patch.object(settings, "email_mode", "development"):
            res_invite = await client.post(
                f"/organizations/{org_id}/invite",
                json={"email": "dev_invitee@example.com"},
                headers=headers,
            )
            assert res_invite.status_code == 201
            data = res_invite.json()
            assert data["token"] is not None
            assert data["invitation_url"] is not None
            assert "/invitations?token=" in data["invitation_url"]
            assert data["delivery_mode"] in ("manual", "development")
            assert data["delivery_status"] == "manual_sharing_required"
            assert "Development Mode" in data["message"] or "Free plan" in data["message"]
