"""
Delayed job scheduling via RQ.

Uses RQ's enqueue_in for deferred execution.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Callable

from rq import Retry

from app.core.config import get_settings
from app.jobs.queue import QUEUE_DEFAULT, get_queue_by_name

logger = logging.getLogger(__name__)
settings = get_settings()


def schedule_job(
    func: Callable[..., Any],
    delay: timedelta,
    *args: Any,
    queue_name: str = QUEUE_DEFAULT,
    **kwargs: Any,
) -> str:
    """
    Schedule a job to run after a delay.

    Returns the RQ job ID.
    """
    current_settings = get_settings()
    if current_settings.job_sync_mode:
        logger.info("Job sync mode: executing scheduled %s immediately", func.__name__)
        func(*args, **kwargs)
        return "sync-mode"

    retry = Retry(
        max=current_settings.rq_retry_max,
        interval=current_settings.rq_retry_interval_list,
    )
    queue = get_queue_by_name(queue_name)
    job = queue.enqueue_in(
        delay,
        func,
        *args,
        **kwargs,
        retry=retry,
        result_ttl=current_settings.rq_result_ttl,
        failure_ttl=current_settings.rq_failure_ttl,
    )
    logger.info(
        "Job scheduled: job_id=%s queue=%s delay=%ss",
        job.id,
        queue_name,
        delay.total_seconds(),
    )
    return job.id

