"""
Redis infrastructure layer.

Provides centralized Redis client with connection management,
health checks, and graceful shutdown. All Redis operations
should go through RedisService or CacheService.
"""

import logging
import ssl
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisClient:
    """Singleton Redis client with connection management."""

    _instance: Redis | None = None

    @staticmethod
    def build_url() -> str:
        """Build Redis URL from settings."""
        if settings.redis_url and settings.redis_url != "redis://localhost:6379":
            return settings.redis_url
        
        # Build URL from individual settings
        scheme = "rediss" if settings.redis_url and settings.redis_url.startswith("rediss") else "redis"
        host = settings.redis_host or "localhost"
        port = settings.redis_port
        password = settings.redis_password
        db = settings.redis_db
        
        if password:
            return f"{scheme}://:{password}@{host}:{port}/{db}"
        return f"{scheme}://{host}:{port}/{db}"

    @classmethod
    def connection_kwargs(cls, url: str) -> dict[str, Any]:
        """Extra connection options (TLS for Upstash rediss:// URLs)."""
        kwargs: dict[str, Any] = {
            "encoding": "utf-8",
            "decode_responses": True,
            "socket_connect_timeout": 10,
            "socket_keepalive": True,
            "health_check_interval": 30,
        }
        if url.startswith("rediss://"):
            kwargs["ssl_cert_reqs"] = "required"
        return kwargs

    @classmethod
    async def get_client(cls) -> Redis:
        """Get or create Redis client instance."""
        if cls._instance is None:
            cls._instance = await cls._create_client()
        return cls._instance

    @classmethod
    async def _create_client(cls) -> Redis:
        """Create new Redis client with connection pool."""
        url = cls.build_url()
        client = redis.from_url(url, **cls.connection_kwargs(url))
        
        # Verify connection
        try:
            await client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
        
        return client

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection."""
        if cls._instance:
            try:
                await cls._instance.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
            finally:
                cls._instance = None

    @classmethod
    async def health_check(cls) -> bool:
        """Check if Redis is healthy."""
        try:
            client = await cls.get_client()
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


@asynccontextmanager
async def get_redis() -> AsyncIterator[Redis]:
    """Context manager for Redis client."""
    client = await RedisClient.get_client()
    try:
        yield client
    except Exception as e:
        logger.error(f"Redis operation error: {e}")
        raise


def get_redis_sync() -> RedisClient:
    """Get RedisClient instance (for dependency injection)."""
    return RedisClient()
