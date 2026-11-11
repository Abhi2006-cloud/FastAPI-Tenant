"""Unit tests for Embedded RQ Worker thread lifecycle and management."""

import threading
from unittest.mock import MagicMock, patch
import pytest
from rq import Queue

from app.core.config import get_settings
from app.jobs.embedded_worker import EmbeddedSimpleWorker, EmbeddedWorkerManager


def test_embedded_worker_flag_off_does_not_start():
    settings = get_settings()
    settings.embedded_worker = False
    settings.job_sync_mode = False

    started = EmbeddedWorkerManager.start()
    assert started is False
    assert EmbeddedWorkerManager.is_alive() is False


def test_embedded_worker_flag_on_start_and_stop_cleanly():
    settings = get_settings()
    settings.embedded_worker = True
    settings.job_sync_mode = False

    mock_conn = MagicMock()
    mock_conn.info.return_value = {"redis_version": "7.0.0"}
    mock_conn.connection_pool.connection_kwargs = {"socket_timeout": 30}
    real_queue = Queue("default", connection=mock_conn)

    stop_event = threading.Event()

    def fake_work(*args, **kwargs):
        stop_event.wait(timeout=5.0)
        return True

    def fake_request_stop(*args, **kwargs):
        stop_event.set()

    with patch("app.jobs.embedded_worker.get_sync_redis_connection", return_value=mock_conn), \
         patch("app.jobs.embedded_worker.get_queue_by_name", return_value=real_queue), \
         patch.object(EmbeddedSimpleWorker, "work", side_effect=fake_work), \
         patch.object(EmbeddedSimpleWorker, "request_stop", side_effect=fake_request_stop):

        started = EmbeddedWorkerManager.start()
        assert started is True
        assert EmbeddedWorkerManager.is_alive() is True

        # Idempotency / Guard against double start
        double_started = EmbeddedWorkerManager.start()
        assert double_started is False
        assert EmbeddedWorkerManager.is_alive() is True

        # Stop worker
        stopped = EmbeddedWorkerManager.stop(timeout=5.0)
        assert stopped is True
        assert EmbeddedWorkerManager.is_alive() is False


def test_embedded_worker_status_modes():
    settings = get_settings()

    # Sync mode
    settings.job_sync_mode = True
    settings.embedded_worker = False
    status_sync = EmbeddedWorkerManager.get_status()
    assert status_sync["mode"] == "sync"
    assert status_sync["alive"] is True

    # External mode
    settings.job_sync_mode = False
    settings.embedded_worker = False
    status_external = EmbeddedWorkerManager.get_status()
    assert status_external["mode"] == "external"

    # Embedded mode
    settings.embedded_worker = True
    status_embedded = EmbeddedWorkerManager.get_status()
    assert status_embedded["mode"] == "embedded"
    assert "queues" in status_embedded


@pytest.mark.asyncio
async def test_health_reports_worker_mode(client):
    settings = get_settings()
    settings.job_sync_mode = False
    settings.embedded_worker = True

    with patch.object(EmbeddedWorkerManager, "is_alive", return_value=True):
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["worker"]["mode"] == "embedded"
        assert data["worker"]["alive"] is True
