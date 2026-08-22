import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import httpx
from fastapi import status

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_current_membership, get_organization_id_header
from app.main import app
from app.infrastructure.search.client import (
    search_client, 
    CircuitBreaker, 
    MeilisearchUnavailableException, 
    MeilisearchApiError
)
from app.infrastructure.search.index_manager import IndexManager
from app.infrastructure.search.document_mapper import (
    map_organization, 
    map_member, 
    map_file, 
    map_audit_log
)
from app.infrastructure.search.service import SearchService
from app.infrastructure.search.repository import SearchRepository
from app.modules.search.models import SearchIndexFailure
from app.modules.memberships.models import MembershipRole
from app.jobs.search_tasks import (
    index_organization_task,
    index_member_task,
    index_file_task,
    index_audit_log_task,
    handle_job_failure
)

# Helper fixtures for mocking settings
@pytest.fixture(autouse=True)
def setup_settings():
    settings = get_settings()
    settings.meilisearch_url = "http://localhost:7700"
    settings.meilisearch_api_key = "test-key"
    settings.meilisearch_index_prefix = "ai_workspace"
    yield


@pytest.fixture(autouse=True)
def reset_search_client():
    """Reset the global search_client singleton state before and after each test."""
    search_client.enabled = False
    search_client.circuit_breaker.state = "CLOSED"
    search_client.circuit_breaker.failure_count = 0
    yield
    search_client.enabled = False
    search_client.circuit_breaker.state = "CLOSED"
    search_client.circuit_breaker.failure_count = 0


@pytest.fixture
def cache_service():
    """Mock CacheService with actual in-memory dict storage."""
    store = {}
    service = MagicMock()
    
    async def mock_get(key):
        return store.get(key)
        
    async def mock_set(key, val, ttl=None):
        import json
        if isinstance(val, (dict, list)):
            store[key] = json.dumps(val)
        else:
            store[key] = str(val)
        return True
        
    async def mock_invalidate_pattern(pattern):
        store.clear()
        return 1
        
    async def mock_delete(key):
        store.pop(key, None)
        return True
        
    service.get.side_effect = mock_get
    service.set.side_effect = mock_set
    service.invalidate_pattern.side_effect = mock_invalidate_pattern
    service.delete.side_effect = mock_delete
    return service


# ---------------------------------------------------------
# Circuit Breaker Tests
# ---------------------------------------------------------
def test_circuit_breaker_flow():
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
    
    assert breaker.allow_request() is True
    assert breaker.state == "CLOSED"
    
    # 1. First failure
    breaker.record_failure()
    assert breaker.state == "CLOSED"
    
    # 2. Second failure
    breaker.record_failure()
    assert breaker.state == "CLOSED"
    
    # 3. Third failure -> transitions to OPEN
    breaker.record_failure()
    assert breaker.state == "OPEN"
    assert breaker.allow_request() is False
    
    # 4. Cooldown wait
    time.sleep(0.12)
    # allow_request will transition state to HALF_OPEN and return True
    assert breaker.allow_request() is True
    assert breaker.state == "HALF_OPEN"
    
    # 5. Success transitions back to CLOSED
    breaker.record_success()
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0


# ---------------------------------------------------------
# SearchClient Tests
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_search_client_connection_success():
    client = search_client
    client._async_client = None
    client.circuit_breaker.state = "CLOSED"
    mock_resp = httpx.Response(200, json={"status": "available"})
    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=mock_resp)
    with (
        patch.object(client, "is_configured", return_value=True),
        patch.object(client, "get_client", return_value=mock_http),
    ):
        connected = await client.initialize()
        assert connected is True
        assert client.enabled is True

        status_val = await client.health_status()
        assert status_val == "connected"


@pytest.mark.asyncio
async def test_search_client_connection_failure():
    client = search_client
    client._async_client = None
    client.circuit_breaker.state = "CLOSED"
    mock_http = AsyncMock()
    mock_http.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    with (
        patch.object(client, "is_configured", return_value=True),
        patch.object(client, "get_client", return_value=mock_http),
    ):
        connected = await client.initialize()
        assert connected is False
        assert client.enabled is False

        status_val = await client.health_status()
        assert status_val == "unavailable"


@pytest.mark.asyncio
async def test_search_client_requests_fail_when_circuit_open():
    client = search_client
    client._async_client = None
    client.enabled = True
    client.circuit_breaker.state = "OPEN"
    client.circuit_breaker.last_state_change = time.time()

    with (
        patch.object(client, "is_configured", return_value=True),
        pytest.raises(MeilisearchUnavailableException),
    ):
        await client.request("GET", "/indexes")




# ---------------------------------------------------------
# IndexManager Tests
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_index_manager_creates_and_configures():
    # Mock Meilisearch client request
    mock_req = AsyncMock()
    # Mock GET /indexes/ai_workspace_organizations to raise 404
    # Mock GET for other indexes to verify workflow
    async def side_effect(method, path, **kwargs):
        if method == "GET" and "indexes/ai_workspace_" in path:
            raise MeilisearchApiError("Not found", 404)
        return {"status": "success"}
    
    mock_req.side_effect = side_effect
    
    with (
        patch("app.infrastructure.search.client.search_client.enabled", True),
        patch("app.infrastructure.search.client.search_client.request", mock_req)
    ):
        await IndexManager.initialize_indexes()
        
        # Verify it tries to GET indexes first, then POST to create, and PATCH for settings
        assert mock_req.call_count >= 12  # (GET, POST, PATCH) x 4 indexes
        
        # Check first create call contains uid
        post_calls = [c for c in mock_req.call_args_list if c[0][0] == "POST"]
        assert len(post_calls) == 4
        assert "uid" in post_calls[0][1]["json"]


# ---------------------------------------------------------
# Document Mapper Tests
# ---------------------------------------------------------
def test_mappers():
    # Organization
    org = MagicMock()
    org.id = uuid4()
    org.name = "My Test Tenant"
    org.owner_id = uuid4()
    org.created_at = datetime.fromtimestamp(1600000000)
    
    doc_org = map_organization(org)
    assert doc_org["id"] == str(org.id)
    assert doc_org["name"] == "My Test Tenant"
    assert doc_org["created_at"] == 1600000000
    
    # Member
    membership = MagicMock()
    membership.id = uuid4()
    membership.user_id = uuid4()
    membership.organization_id = uuid4()
    membership.role = MembershipRole.ADMIN
    membership.user = MagicMock()
    membership.user.email = "member@example.com"
    membership.user.created_at = datetime.fromtimestamp(1600000000)
    
    doc_mem = map_member(membership)
    assert doc_mem["id"] == str(membership.id)
    assert doc_mem["email"] == "member@example.com"
    assert doc_mem["role"] == "admin"
    assert doc_mem["created_at"] == 1600000000


# ---------------------------------------------------------
# SearchService Tests (Tenant Isolation, Cache, Failover)
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_search_service_tenant_filtering_and_caching():
    service = SearchService()
    mock_cache = AsyncMock()
    service.cache = mock_cache
    
    cache_store: dict = {}
    async def mock_get(key): return cache_store.get(key)
    async def mock_set(key, val, **kw): cache_store[key] = val
    async def mock_delete_pattern(pat): cache_store.clear()
    mock_cache.get.side_effect = mock_get
    mock_cache.set.side_effect = mock_set
    mock_cache.invalidate_pattern.side_effect = mock_delete_pattern
    mock_cache.delete_pattern.side_effect = mock_delete_pattern

    org_id = uuid4()
    mock_res = {"hits": [{"id": "doc-123", "organization_id": str(org_id), "file_name": "important.pdf"}], "totalHits": 1}

    search_client.enabled = True
    search_client.circuit_breaker.state = "CLOSED"

    # Mock SearchRepository.search and index_document calls
    with (
        patch.object(search_client, "is_configured", return_value=True),
        patch.object(service.repo, "search", new_callable=AsyncMock, return_value=mock_res) as mock_search,
        patch.object(service.repo, "index_document", new_callable=AsyncMock, return_value=None) as mock_index
    ):
        # 1. Search (Cache Miss)
        res1 = await service.search("files", "important", org_id)
        assert res1 == mock_res
        mock_search.assert_called_once()

        # 2. Repeated Search (Cache Hit)
        res2 = await service.search("files", "important", org_id)
        assert res2 == mock_res
        # Repository should NOT be called again due to caching
        assert mock_search.call_count == 1

        # 3. Index update invalidates cache
        await service.index_document("files", "doc-123", {"id": "doc-123", "organization_id": str(org_id)})

        # 4. Search again (Cache Miss after invalidation)
        res3 = await service.search("files", "important", org_id)
        assert res3 == mock_res
        assert mock_search.call_count == 2


@pytest.mark.asyncio
async def test_global_search_aggregates(cache_service):
    service = SearchService()
    service.cache = cache_service
    org_id = uuid4()
    
    # Mock individual searches
    mock_hits = {"hits": [{"id": "hit-1"}], "totalHits": 1}
    
    with (
        patch("app.infrastructure.search.client.search_client.enabled", True),
        patch("app.infrastructure.search.client.search_client.is_configured", return_value=True),
        patch.object(SearchService, "search", return_value=mock_hits) as mock_service_search
    ):
        res = await service.global_search("query", org_id)
        assert len(res["files"]) == 1
        assert len(res["members"]) == 1
        assert len(res["audit_logs"]) == 1
        assert mock_service_search.call_count == 3


# ---------------------------------------------------------
# Background Indexing & DB Logging Tests
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_db_session_failure_saves_directly_to_db(db_engine):
    """Directly tests the async record_indexing_failure DB save path using custom sessionmaker."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    my_session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    
    service = SearchService()
    
    with patch("app.infrastructure.search.service.async_session_factory", my_session_factory):
        await service.record_indexing_failure(
            job_id="rq-job-222",
            index_name="files",
            doc_id="file-uuid-2",
            operation="index",
            error_message="Test DB persistence error description",
            payload={"filename": "important.doc"}
        )
    
    from sqlalchemy import select
    async with my_session_factory() as check_session:
        result = await check_session.execute(select(SearchIndexFailure))
        failures = list(result.scalars().all())
    
    assert len(failures) == 1
    assert failures[0].job_id == "rq-job-222"
    assert failures[0].index_name == "files"
    assert failures[0].document_id == "file-uuid-2"
    assert failures[0].error_message == "Test DB persistence error description"
    assert failures[0].payload == {"filename": "important.doc"}


@pytest.mark.asyncio
async def test_job_failure_triggers_correctly():
    # Mock RQ current job
    mock_job = MagicMock()
    mock_job.id = "rq-job-111"
    mock_job.retries_left = 0
    
    exc = Exception("Meilisearch API key has expired.")
    
    # Mock the record_indexing_failure to prevent cross-loop sqlite failures
    mock_save = AsyncMock()
    
    with (
        patch("app.jobs.search_tasks.get_current_job", return_value=mock_job),
        patch("app.infrastructure.search.service.SearchService.record_indexing_failure", mock_save),
        patch("app.jobs.tasks.logger.error")
    ):
        # Trigger failure callback
        handle_job_failure(
            exc=exc,
            index_name="files",
            doc_id="file-uuid",
            operation="index",
            payload={"filename": "leaked.txt"}
        )
        
        # Verify it invoked record_indexing_failure via run_async
        mock_save.assert_called_once_with(
            job_id="rq-job-111",
            index_name="files",
            doc_id="file-uuid",
            operation="index",
            error_message="Meilisearch API key has expired.",
            payload={"filename": "leaked.txt"}
        )


# ---------------------------------------------------------
# Graceful Degradation / Routing HTTP 503 Tests
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_health_check_graceful_degradation(client):
    # Mock Search health to check health degraded status
    with patch("app.infrastructure.search.health.check_search_health", new_callable=AsyncMock, return_value="unavailable"):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["search"] == "unavailable"



@pytest.mark.asyncio
async def test_search_endpoints_return_503_when_offline(client):
    headers = {"X-Organization-Id": str(uuid4())}
    
    # Define dependency overrides to pass authentication
    mock_user = MagicMock()
    mock_user.id = uuid4()
    
    mock_membership = MagicMock()
    mock_membership.id = uuid4()
    mock_membership.role = MembershipRole.MEMBER
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_organization_id_header] = lambda: uuid4()
    app.dependency_overrides[get_current_membership] = lambda: mock_membership
    
    # Mocking SearchService.global_search to raise MeilisearchUnavailableException
    try:
        with patch.object(SearchService, "global_search", side_effect=MeilisearchUnavailableException("Search offline")):
            response = await client.get("/search?q=test", headers=headers)
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert response.json()["detail"] == "Search service is temporarily unavailable."
    finally:
        app.dependency_overrides.clear()
