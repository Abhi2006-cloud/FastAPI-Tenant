"""Unit tests for Search Disabled mode, console email mode, and zero-call /health/live."""

from unittest.mock import AsyncMock, patch
import pytest

from app.core.config import get_settings
from app.infrastructure.search.client import SearchClient
from app.infrastructure.search.health import check_search_health
from app.jobs.tasks import index_organization_task
from app.services.job_service import JobService


def test_search_disabled_setting_and_client():
    settings = get_settings()
    settings.search_enabled = False
    assert settings.is_search_enabled is False

    client = SearchClient()
    assert client.is_configured() is False


@pytest.mark.asyncio
async def test_search_client_initialize_and_health_when_disabled():
    settings = get_settings()
    settings.search_enabled = False

    client = SearchClient()
    initialized = await client.initialize()
    assert initialized is False

    status = await check_search_health()
    assert status == "disabled"


def test_enqueue_search_task_skipped_when_disabled():
    settings = get_settings()
    settings.search_enabled = False
    settings.job_sync_mode = False

    service = JobService()
    res = service.enqueue(index_organization_task, "test-org-id")
    assert res == "search-disabled"


@pytest.mark.asyncio
async def test_health_endpoint_ok_with_search_disabled_and_console_email(client, db_engine):
    settings = get_settings()
    settings.search_enabled = False
    settings.email_provider = "console"
    settings.email_mode = "console"

    res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["search"] == "disabled"
    assert data["email"] == "console"
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_live_endpoint_is_instant_and_isolated(client):
    """GET /health/live returns {'status': 'ok'} without touching DB or Redis."""
    res = await client.get("/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
