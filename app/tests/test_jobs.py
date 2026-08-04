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
    response = await client.get(
        "/jobs/sync-mode",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "sync-mode"
    assert body["status"] == "finished"


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
