"""
RQ (Redis Queue) connection layer.

Provides a synchronous Redis connection for RQ workers and job enqueueing.
Reuses the same Redis URL and connection options as the async RedisClient.
"""

import logging
from functools import lru_cache

import redis as sync_redis
from redis import Redis
from rq import Queue

from app.core.config import get_settings
from app.core.redis import RedisClient

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache
def get_sync_redis_connection() -> Redis:
    """Get or create the synchronous Redis connection used by RQ."""
    url = RedisClient.build_url()
    kwargs = RedisClient.connection_kwargs(url)
    kwargs["decode_responses"] = False  # RQ uses binary pickle for job data
    client = sync_redis.from_url(url, **kwargs)
    client.ping()
    logger.info("RQ sync Redis connection established")
    return client



def get_queue(name: str) -> Queue:
    """Return an RQ queue bound to the shared Redis connection."""
    return Queue(
        name,
        connection=get_sync_redis_connection(),
        default_timeout=settings.rq_job_timeout,
    )


def get_all_queues() -> list[Queue]:
    """Return all configured RQ queues."""
    from app.jobs.queue import QUEUE_NAMES

    return [get_queue(name) for name in QUEUE_NAMES]
