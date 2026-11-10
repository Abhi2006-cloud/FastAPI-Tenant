"""
Tests for background job infrastructure (v2.1.0).

Covers queue creation, job enqueue, execution, retry, failure,
status endpoint, and worker startup configuration.
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from rq import Retry

from app.jobs.job_status import build_job_status_payload, map_rq_status
from app.jobs.queue import QUEUE_DEFAULT, QUEUE_HIGH, QUEUE_LOW, QUEUE_NAMES, get_default_queue
from app.jobs.tasks import process_invitation_task, record_audit_event_task
from app.jobs.worker import main as worker_main
from app.services.job_service import JobService


def test_queue_names_defined() -> None:
    assert QUEUE_DEFAULT == "default"
    assert QUEUE_HIGH == "high"
    assert QUEUE_LOW == "low"
    assert len(QUEUE_NAMES) == 4



def test_map_rq_status() -> None:
    assert map_rq_status("queued") == "queued"
    assert map_rq_status("started") == "started"
    assert map_rq_status("finished") == "finished"
    assert map_rq_status("failed") == "failed"
    assert map_rq_status("deferred") == "queued"


def test_build_job_status_payload_finished() -> None:
    job = MagicMock()
    job.id = "abc-123"
    job.get_status.return_value = "finished"
    job.origin = "default"
    job.created_at = None
    job.started_at = None
    job.ended_at = None
    job.result = {"ok": True}
    job.exc_info = None

    payload = build_job_status_payload(job)
    assert payload["job_id"] == "abc-123"
    assert payload["status"] == "finished"
    assert payload["result"] == {"ok": True}


def test_job_service_enqueue_sync_mode() -> None:
    called = []

    def sample_task(value: str) -> str:
        called.append(value)
        return value

    service = JobService()
    job_id = service.enqueue(sample_task, "test-value")
    assert job_id == "sync-mode"
    assert called == ["test-value"]


def test_job_service_priority_enqueue_sync_mode() -> None:
    results = []

    def task(name: str) -> None:
        results.append(name)

    service = JobService()
    service.enqueue_high_priority(task, "high")
    service.enqueue_low_priority(task, "low")
    assert results == ["high", "low"]


def test_record_audit_event_task_executes() -> None:
    """Audit task delegates to persist helper and returns audit_log_id."""
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock
    from uuid import uuid4

    fake_log = MagicMock()
    fake_log.id = uuid4()

    async def _fake_persist(*_args, **_kwargs):
        return fake_log

    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    @asynccontextmanager
    async def _fake_session():
        yield session

    with (
        patch("app.jobs.tasks.persist_audit_event", side_effect=_fake_persist),
        patch("app.jobs.tasks.async_session_factory", _fake_session),
    ):
        result = record_audit_event_task(
            organization_id=str(uuid4()),
            actor_user_id=str(uuid4()),
            action="ORGANIZATION_CREATED",
            resource_type="organization",
            resource_id=str(uuid4()),
            metadata={"name": "Test"},
        )
    assert result["audit_log_id"] == str(fake_log.id)


def test_process_invitation_task() -> None:
    result = process_invitation_task(
        invitation_id="inv-1",
        organization_id="org-1",
        email="user@example.com",
        inviter_id="user-1",
    )
    assert result["status"] == "processed"
    assert result["email"] == "user@example.com"


def test_job_service_get_job_sync_mode() -> None:
    service = JobService()
    job = service.get_job("sync-mode")
    assert job is not None
    assert job["status"] == "finished"


@patch("app.services.job_service.get_queue_by_name")
def test_job_service_enqueue_with_rq(mock_get_queue) -> None:
    mock_queue = MagicMock()
    mock_job = MagicMock()
    mock_job.id = "job-xyz"
    mock_queue.enqueue.return_value = mock_job
    mock_get_queue.return_value = mock_queue

    mock_settings = MagicMock()
    mock_settings.job_sync_mode = False
    mock_settings.rq_result_ttl = 86400
    mock_settings.rq_failure_ttl = 604800
    mock_settings.rq_retry_max = 3
    mock_settings.rq_retry_interval_list = [10, 30, 60]

    with patch("app.services.job_service.get_settings", return_value=mock_settings):
        service = JobService()
        job_id = service.enqueue(lambda: None)

    assert job_id == "job-xyz"
    mock_queue.enqueue.assert_called_once()


@patch("app.services.job_service.Job.fetch")
@patch("app.services.job_service.get_sync_redis_connection")
def test_job_service_retry_job(mock_conn, mock_fetch) -> None:
    mock_job = MagicMock()
    mock_job.get_status.return_value = "failed"
    mock_fetch.return_value = mock_job

    service = JobService()
    assert service.retry_job("job-1") is True
    mock_job.retry.assert_called_once()


@patch("app.services.job_service.Job.fetch")
@patch("app.services.job_service.get_sync_redis_connection")
def test_job_service_cancel_job(mock_conn, mock_fetch) -> None:
    mock_job = MagicMock()
    mock_job.get_status.return_value = "queued"
    mock_fetch.return_value = mock_job

    service = JobService()
    assert service.cancel_job("job-1") is True
    mock_job.cancel.assert_called_once()


@patch("app.jobs.worker.Worker")
@patch("app.jobs.worker.get_sync_redis_connection")
def test_worker_startup(mock_redis, mock_worker_cls) -> None:
    mock_worker = MagicMock()
    mock_worker_cls.return_value = mock_worker

    worker_main()

    mock_worker_cls.assert_called_once()
    mock_worker.work.assert_called_once_with(with_scheduler=True)


@patch("app.core.rq.Queue")
@patch("app.core.rq.get_sync_redis_connection")
def test_get_default_queue(mock_redis, mock_queue_cls) -> None:
    get_default_queue()
    mock_queue_cls.assert_called_once()


@pytest.mark.asyncio
async def test_job_status_endpoint_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/jobs/sync-mode")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_job_status_endpoint(client: AsyncClient) -> None:
    from app.tests.test_audit_logs import _register_and_token

    token = await _register_and_token(client, "jobuser@example.com")
    org_res = await client.post(
        "/organizations",
        json={"name": "Job Test Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert org_res.status_code == 201
    org_id = org_res.json()["id"]

    response = await client.get(
        "/jobs/sync-mode",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org_id,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "sync-mode"
    assert body["status"] == "finished"


@pytest.mark.asyncio
async def test_job_endpoint_requires_org_header_and_membership(client: AsyncClient) -> None:
    from app.tests.test_audit_logs import _register_and_token

    token = await _register_and_token(client, "noorguser@example.com")
    # Missing X-Organization-Id header
    res_no_header = await client.get(
        "/jobs/sync-mode",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_no_header.status_code == 403
    assert "X-Organization-Id header is required" in res_no_header.text

    # With non-existent organization
    import uuid
    res_non_member = await client.get(
        "/jobs/sync-mode",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(uuid.uuid4()),
        },
    )
    assert res_non_member.status_code == 403
    assert "not a member" in res_non_member.text


@pytest.mark.asyncio
async def test_job_endpoint_member_role_rejected(client: AsyncClient) -> None:
    from app.tests.test_memberships import (
        _accept_invitation,
        _add_member_to_org,
        _create_org_and_get_id,
        _register_and_token,
    )

    owner_token = await _register_and_token(client, "jobowner@example.com")
    org_id = await _create_org_and_get_id(client, owner_token)

    # Invite regular member
    invite_token = await _add_member_to_org(client, org_id, "jobregular@example.com", owner_token)
    member_token = await _register_and_token(client, "jobregular@example.com")
    await _accept_invitation(client, member_token, invite_token)

    # Regular member attempts to list jobs or get job status
    member_headers = {
        "Authorization": f"Bearer {member_token}",
        "X-Organization-Id": org_id,
    }
    list_res = await client.get("/jobs", headers=member_headers)
    assert list_res.status_code == 403
    assert "Insufficient permissions" in list_res.text

    get_res = await client.get("/jobs/sync-mode", headers=member_headers)
    assert get_res.status_code == 403
    assert "Insufficient permissions" in get_res.text


@pytest.mark.asyncio
async def test_job_tenant_isolation_cannot_access_other_tenant_job(client: AsyncClient) -> None:
    from app.tests.test_memberships import _create_org_and_get_id, _register_and_token

    owner_a_token = await _register_and_token(client, "ownera@example.com")
    org_a_id = await _create_org_and_get_id(client, owner_a_token)

    owner_b_token = await _register_and_token(client, "ownerb@example.com")
    org_b_id = await _create_org_and_get_id(client, owner_b_token)

    # Mock an RQ job belonging to Org A
    mock_job = MagicMock()
    mock_job.id = "job-org-a-123"
    mock_job.get_status.return_value = "finished"
    mock_job.origin = "default"
    mock_job.created_at = None
    mock_job.started_at = None
    mock_job.ended_at = None
    mock_job.result = {"status": "ok"}
    mock_job.exc_info = None
    mock_job.meta = {"organization_id": org_a_id}

    with (
        patch("app.services.job_service.Job.fetch", return_value=mock_job),
        patch("app.services.job_service.get_sync_redis_connection", return_value=MagicMock()),
    ):
        # Owner B tries to fetch Org A's job using Org B's context -> 404 (isolation enforced)
        res_b = await client.get(
            f"/jobs/{mock_job.id}",
            headers={
                "Authorization": f"Bearer {owner_b_token}",
                "X-Organization-Id": org_b_id,
            },
        )
        assert res_b.status_code == 404

        # Owner A fetches Org A's job using Org A's context -> 200
        res_a = await client.get(
            f"/jobs/{mock_job.id}",
            headers={
                "Authorization": f"Bearer {owner_a_token}",
                "X-Organization-Id": org_a_id,
            },
        )
        assert res_a.status_code == 200
        assert res_a.json()["job_id"] == mock_job.id


def test_job_payload_does_not_leak_stack_traces_or_secrets() -> None:
    # 1. Failed job masks internal stack traces and paths
    mock_failed_job = MagicMock()
    mock_failed_job.id = "job-err-1"
    mock_failed_job.get_status.return_value = "failed"
    mock_failed_job.origin = "default"
    mock_failed_job.created_at = None
    mock_failed_job.started_at = None
    mock_failed_job.ended_at = None
    mock_failed_job.result = None
    mock_failed_job.exc_info = (
        "Traceback (most recent call last):\n"
        '  File "/app/services/internal.py", line 42, in process_data\n'
        '    secret = "db_pass_123"\n'
        "ValueError: Invalid configuration value provided"
    )

    failed_payload = build_job_status_payload(mock_failed_job)
    assert failed_payload["status"] == "failed"
    assert "/app/services/internal.py" not in failed_payload["error"]
    assert "db_pass_123" not in failed_payload["error"]
    assert failed_payload["error"] == "ValueError: Invalid configuration value provided"

    # 2. Finished job masks sensitive keys in result
    mock_finished_job = MagicMock()
    mock_finished_job.id = "job-ok-1"
    mock_finished_job.get_status.return_value = "finished"
    mock_finished_job.origin = "default"
    mock_finished_job.created_at = None
    mock_finished_job.started_at = None
    mock_finished_job.ended_at = None
    mock_finished_job.result = {"secret_token": "supersecret123", "data": "safe"}
    mock_finished_job.exc_info = None

    finished_payload = build_job_status_payload(mock_finished_job)
    assert finished_payload["status"] == "finished"
    assert finished_payload["result"]["secret_token"] == "***"
    assert finished_payload["result"]["data"] == "safe"


@pytest.mark.asyncio
async def test_health_includes_worker_and_queue_status(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "worker" in body
    assert "workers" in body
    assert "queues" in body


def test_retry_configuration() -> None:
    retry = Retry(max=3, interval=[10, 30, 60])
    assert retry.max == 3
