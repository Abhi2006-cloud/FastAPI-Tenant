"""
Cache infrastructure layer.

Provides centralized cache key builder, TTL constants,
CacheService (Cache-Aside pattern), and RedisService.
All caching operations should go through these services.
"""

import json
import logging
from typing import Any

from app.core.redis import RedisClient

logger = logging.getLogger(__name__)


class CacheKeyBuilder:
    """Centralized cache key builder with namespaces."""

    # Namespaces
    USER = "user"
    ORGANIZATION = "organization"
    MEMBERSHIP = "membership"
    INVITATION = "invitation"
    FILE = "file"
    AUDIT = "audit"

    @staticmethod
    def user(user_id: str) -> str:
        """Build user cache key."""
        return f"{CacheKeyBuilder.USER}:{user_id}"

    @staticmethod
    def organization(org_id: str) -> str:
        """Build organization cache key."""
        return f"{CacheKeyBuilder.ORGANIZATION}:{org_id}"

    @staticmethod
    def organization_members(org_id: str) -> str:
        """Build organization members cache key."""
        return f"{CacheKeyBuilder.ORGANIZATION}:{org_id}:members"

    @staticmethod
    def organization_files(org_id: str) -> str:
        """Build organization files cache key."""
        return f"{CacheKeyBuilder.ORGANIZATION}:{org_id}:files"

    @staticmethod
    def membership(user_id: str, org_id: str) -> str:
        """Build membership cache key."""
        return f"{CacheKeyBuilder.MEMBERSHIP}:{user_id}:{org_id}"

    @staticmethod
    def invitation(invite_id: str) -> str:
        """Build invitation cache key."""
        return f"{CacheKeyBuilder.INVITATION}:{invite_id}"

    @staticmethod
    def file(file_id: str) -> str:
        """Build file cache key."""
        return f"{CacheKeyBuilder.FILE}:{file_id}"

    @staticmethod
    def audit_logs(org_id: str) -> str:
        """Build audit logs cache key."""
        return f"{CacheKeyBuilder.AUDIT}:{org_id}"


class CacheTTL:
    """Centralized TTL configuration in seconds."""

    # Short TTL (5 minutes)
    SHORT = 300

    # Medium TTL (15 minutes)
    MEDIUM = 900

    # Long TTL (1 hour)
    LONG = 3600

    # Very Long TTL (24 hours)
    VERY_LONG = 86400

    # Default TTL
    DEFAULT = MEDIUM


class RedisService:
    """Low-level Redis service wrapping Redis operations."""

    def __init__(self) -> None:
        self._client = RedisClient()

    async def get(self, key: str) -> str | None:
        """Get value by key."""
        try:
            client = await self._client.get_client()
            return await client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: str) -> bool:
        """Set value by key (no expiration)."""
        try:
            client = await self._client.get_client()
            await client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def set_with_ttl(self, key: str, value: str, ttl: int) -> bool:
        """Set value by key with TTL in seconds."""
        try:
            client = await self._client.get_client()
            await client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis SETEX error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key."""
        try:
            client = await self._client.get_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            client = await self._client.get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key."""
        try:
            client = await self._client.get_client()
            await client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """Get remaining time to live for key."""
        try:
            client = await self._client.get_client()
            return await client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
            return -1

    async def increment(self, key: str) -> int:
        """Increment value by key."""
        try:
            client = await self._client.get_client()
            return await client.incr(key)
        except Exception as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return 0

    async def decrement(self, key: str) -> int:
        """Decrement value by key."""
        try:
            client = await self._client.get_client()
            return await client.decr(key)
        except Exception as e:
            logger.error(f"Redis DECR error for key {key}: {e}")
            return 0

    async def keys(self, pattern: str) -> list[str]:
        """Get keys matching pattern."""
        try:
            client = await self._client.get_client()
            return await client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS error for pattern {pattern}: {e}")
            return []

    async def flush_namespace(self, namespace: str) -> int:
        """Delete all keys matching namespace pattern."""
        try:
            pattern = f"{namespace}:*"
            keys = await self.keys(pattern)
            if keys:
                client = await self._client.get_client()
                await client.delete(*keys)
                logger.info(f"Flushed {len(keys)} keys matching pattern: {pattern}")
            return len(keys)
        except Exception as e:
            logger.error(f"Redis FLUSH_NAMESPACE error for {namespace}: {e}")
            return 0

    async def json_set(self, key: str, value: dict, ttl: int | None = None) -> bool:
        """Set JSON value (future-ready for RedisJSON)."""
        try:
            json_str = json.dumps(value)
            if ttl:
                return await self.set_with_ttl(key, json_str, ttl)
            return await self.set(key, json_str)
        except Exception as e:
            logger.error(f"Redis JSON_SET error for key {key}: {e}")
            return False

    async def json_get(self, key: str) -> dict | None:
        """Get JSON value (future-ready for RedisJSON)."""
        try:
            value = await self.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis JSON_GET error for key {key}: {e}")
            return None


class CacheService:
    """High-level cache service implementing Cache-Aside pattern."""

    def __init__(self) -> None:
        self._redis = RedisService()

    async def get(self, key: str) -> Any | None:
        """Get cached value."""
        try:
            value = await self._redis.get(key)
            if value:
                logger.debug(f"Cache HIT for key: {key}")
                return value
            logger.debug(f"Cache MISS for key: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = CacheTTL.DEFAULT) -> bool:
        """Set value in cache with TTL."""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            else:
                value = str(value)
            return await self._redis.set_with_ttl(key, value, ttl)
        except Exception as e:
            logger.error(f"Cache SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            result = await self._redis.delete(key)
            if result:
                logger.debug(f"Cache INVALIDATED for key: {key}")
            return result
        except Exception as e:
            logger.error(f"Cache DELETE error for key {key}: {e}")
            return False

    async def invalidate(self, key: str) -> bool:
        """Alias for delete(); invalidates a single cache key."""
        return await self.delete(key)

    async def set_with_ttl(self, key: str, value: Any, ttl: int = CacheTTL.DEFAULT) -> bool:
        """Set value in cache with explicit TTL."""
        return await self.set(key, value, ttl)

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                client = await self._redis._client.get_client()
                await client.delete(*keys)
                logger.info(f"Cache INVALIDATED pattern: {pattern} ({len(keys)} keys)")
            return len(keys)
        except Exception as e:
            logger.error(f"Cache INVALIDATE_PATTERN error for {pattern}: {e}")
            return 0

    async def get_or_set(
        self,
        key: str,
        factory: callable,
        ttl: int = CacheTTL.DEFAULT,
    ) -> Any:
        """
        Get value from cache or compute and store it.
        
        Args:
            key: Cache key
            factory: Async function to compute value if cache miss
            ttl: Time to live in seconds
            
        Returns:
            Cached or computed value
        """
        # Try cache first
        cached = await self.get(key)
        if cached is not None:
            try:
                return json.loads(cached) if cached.startswith(("{", "[")) else cached
            except json.JSONDecodeError:
                return cached

        # Cache miss - compute value
        try:
            value = await factory()
            if value is not None:
                await self.set(key, value, ttl)
            return value
        except Exception as e:
            logger.error(f"Error in cache factory for key {key}: {e}")
            raise

    async def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all keys in namespace."""
        return await self._redis.flush_namespace(namespace)

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return await self._redis.exists(key)
