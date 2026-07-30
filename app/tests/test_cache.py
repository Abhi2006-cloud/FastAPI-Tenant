"""
Cache infrastructure tests.

Tests for RedisService, CacheService, and cache integration.
Uses mocked Redis to avoid requiring live Redis during tests.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cache import CacheKeyBuilder, CacheService, CacheTTL, RedisService


@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    client = AsyncMock()
    client.ping = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.setex = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=0)
    client.expire = AsyncMock(return_value=True)
    client.ttl = AsyncMock(return_value=300)
    client.incr = AsyncMock(return_value=1)
    client.decr = AsyncMock(return_value=0)
    client.keys = AsyncMock(return_value=[])
    return client


@pytest.fixture
def redis_service(mock_redis_client):
    """RedisService with mocked client."""
    with patch("app.core.redis.RedisClient.get_client", return_value=mock_redis_client):
        service = RedisService()
        yield service


@pytest.fixture
def cache_service(redis_service):
    """CacheService with mocked RedisService."""
    with patch.object(RedisService, "__init__", lambda self: None):
        service = CacheService()
        service._redis = redis_service
        yield service


class TestCacheKeyBuilder:
    """Test cache key builder."""

    def test_user_key(self):
        key = CacheKeyBuilder.user("user-123")
        assert key == "user:user-123"

    def test_organization_key(self):
        key = CacheKeyBuilder.organization("org-456")
        assert key == "organization:org-456"

    def test_organization_members_key(self):
        key = CacheKeyBuilder.organization_members("org-456")
        assert key == "organization:org-456:members"

    def test_organization_files_key(self):
        key = CacheKeyBuilder.organization_files("org-456")
        assert key == "organization:org-456:files"

    def test_membership_key(self):
        key = CacheKeyBuilder.membership("user-123", "org-456")
        assert key == "membership:user-123:org-456"

    def test_invitation_key(self):
        key = CacheKeyBuilder.invitation("invite-789")
        assert key == "invitation:invite-789"

    def test_file_key(self):
        key = CacheKeyBuilder.file("file-abc")
        assert key == "file:file-abc"

    def test_audit_logs_key(self):
        key = CacheKeyBuilder.audit_logs("org-456")
        assert key == "audit:org-456"


class TestCacheTTL:
    """Test TTL constants."""

    def test_short_ttl(self):
        assert CacheTTL.SHORT == 300  # 5 minutes

    def test_medium_ttl(self):
        assert CacheTTL.MEDIUM == 900  # 15 minutes

    def test_long_ttl(self):
        assert CacheTTL.LONG == 3600  # 1 hour

    def test_very_long_ttl(self):
        assert CacheTTL.VERY_LONG == 86400  # 24 hours

    def test_default_ttl(self):
        assert CacheTTL.DEFAULT == CacheTTL.MEDIUM


class TestRedisService:
    """Test RedisService operations."""

    @pytest.mark.asyncio
    async def test_get(self, redis_service, mock_redis_client):
        mock_redis_client.get.return_value = "test-value"
        value = await redis_service.get("test-key")
        assert value == "test-value"
        mock_redis_client.get.assert_called_once_with("test-key")

    @pytest.mark.asyncio
    async def test_get_none(self, redis_service, mock_redis_client):
        mock_redis_client.get.return_value = None
        value = await redis_service.get("test-key")
        assert value is None

    @pytest.mark.asyncio
    async def test_set(self, redis_service, mock_redis_client):
        result = await redis_service.set("test-key", "test-value")
        assert result is True
        mock_redis_client.set.assert_called_once_with("test-key", "test-value")

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, redis_service, mock_redis_client):
        result = await redis_service.set_with_ttl("test-key", "test-value", 300)
        assert result is True
        mock_redis_client.setex.assert_called_once_with("test-key", 300, "test-value")

    @pytest.mark.asyncio
    async def test_delete(self, redis_service, mock_redis_client):
        result = await redis_service.delete("test-key")
        assert result is True
        mock_redis_client.delete.assert_called_once_with("test-key")

    @pytest.mark.asyncio
    async def test_exists_true(self, redis_service, mock_redis_client):
        mock_redis_client.exists.return_value = 1
        result = await redis_service.exists("test-key")
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, redis_service, mock_redis_client):
        mock_redis_client.exists.return_value = 0
        result = await redis_service.exists("test-key")
        assert result is False

    @pytest.mark.asyncio
    async def test_expire(self, redis_service, mock_redis_client):
        result = await redis_service.expire("test-key", 600)
        assert result is True
        mock_redis_client.expire.assert_called_once_with("test-key", 600)

    @pytest.mark.asyncio
    async def test_ttl(self, redis_service, mock_redis_client):
        mock_redis_client.ttl.return_value = 300
        result = await redis_service.ttl("test-key")
        assert result == 300

    @pytest.mark.asyncio
    async def test_increment(self, redis_service, mock_redis_client):
        mock_redis_client.incr.return_value = 5
        result = await redis_service.increment("counter")
        assert result == 5

    @pytest.mark.asyncio
    async def test_decrement(self, redis_service, mock_redis_client):
        mock_redis_client.decr.return_value = 3
        result = await redis_service.decrement("counter")
        assert result == 3

    @pytest.mark.asyncio
    async def test_keys(self, redis_service, mock_redis_client):
        mock_redis_client.keys.return_value = ["key1", "key2", "key3"]
        result = await redis_service.keys("pattern:*")
        assert result == ["key1", "key2", "key3"]

    @pytest.mark.asyncio
    async def test_flush_namespace(self, redis_service, mock_redis_client):
        mock_redis_client.keys.return_value = ["ns:key1", "ns:key2"]
        result = await redis_service.flush_namespace("ns")
        assert result == 2
        mock_redis_client.delete.assert_called_once_with("ns:key1", "ns:key2")

    @pytest.mark.asyncio
    async def test_json_set(self, redis_service, mock_redis_client):
        data = {"key": "value"}
        result = await redis_service.json_set("test-key", data, ttl=300)
        assert result is True
        mock_redis_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_json_get(self, redis_service, mock_redis_client):
        mock_redis_client.get.return_value = json.dumps({"key": "value"})
        result = await redis_service.json_get("test-key")
        assert result == {"key": "value"}


class TestCacheService:
    """Test CacheService operations."""

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache_service, redis_service):
        redis_service.get = AsyncMock(return_value="cached-value")
        value = await cache_service.get("test-key")
        assert value == "cached-value"

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache_service, redis_service):
        redis_service.get = AsyncMock(return_value=None)
        value = await cache_service.get("test-key")
        assert value is None

    @pytest.mark.asyncio
    async def test_set_string(self, cache_service, redis_service):
        redis_service.set_with_ttl = AsyncMock(return_value=True)
        result = await cache_service.set("test-key", "value", ttl=300)
        assert result is True

    @pytest.mark.asyncio
    async def test_set_dict(self, cache_service, redis_service):
        redis_service.set_with_ttl = AsyncMock(return_value=True)
        result = await cache_service.set("test-key", {"key": "value"}, ttl=300)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete(self, cache_service, redis_service):
        redis_service.delete = AsyncMock(return_value=True)
        result = await cache_service.delete("test-key")
        assert result is True

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache_service, redis_service):
        redis_service.keys = AsyncMock(return_value=["key1", "key2"])
        redis_service._client = AsyncMock()
        redis_service._client.delete = AsyncMock()
        result = await cache_service.invalidate_pattern("pattern:*")
        assert result == 2

    @pytest.mark.asyncio
    async def test_get_or_set_cache_hit(self, cache_service, redis_service):
        redis_service.get = AsyncMock(return_value=json.dumps({"cached": True}))
        factory_called = False

        async def factory():
            nonlocal factory_called
            factory_called = True
            return {"computed": True}

        result = await cache_service.get_or_set("test-key", factory)
        assert result == {"cached": True}
        assert factory_called is False

    @pytest.mark.asyncio
    async def test_get_or_set_cache_miss(self, cache_service, redis_service):
        redis_service.get = AsyncMock(return_value=None)
        redis_service.set_with_ttl = AsyncMock(return_value=True)
        factory_called = False

        async def factory():
            nonlocal factory_called
            factory_called = True
            return {"computed": True}

        result = await cache_service.get_or_set("test-key", factory)
        assert result == {"computed": True}
        assert factory_called is True

    @pytest.mark.asyncio
    async def test_get_or_set_factory_error(self, cache_service, redis_service):
        redis_service.get = AsyncMock(return_value=None)

        async def factory():
            raise ValueError("Factory error")

        with pytest.raises(ValueError):
            await cache_service.get_or_set("test-key", factory)

    @pytest.mark.asyncio
    async def test_invalidate_namespace(self, cache_service, redis_service):
        redis_service.flush_namespace = AsyncMock(return_value=5)
        result = await cache_service.invalidate_namespace("organization")
        assert result == 5

    @pytest.mark.asyncio
    async def test_exists(self, cache_service, redis_service):
        redis_service.exists = AsyncMock(return_value=True)
        result = await cache_service.exists("test-key")
        assert result is True

    @pytest.mark.asyncio
    async def test_invalidate_alias(self, cache_service, redis_service):
        redis_service.delete = AsyncMock(return_value=True)
        result = await cache_service.invalidate("test-key")
        assert result is True

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache_service, redis_service):
        redis_service.set_with_ttl = AsyncMock(return_value=True)
        result = await cache_service.set_with_ttl("test-key", {"a": 1}, ttl=CacheTTL.SHORT)
        assert result is True


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_includes_database_and_redis(self, client, db_engine):
        with patch("app.core.database.engine", db_engine):
            response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"
        assert data["redis"] == "connected"
