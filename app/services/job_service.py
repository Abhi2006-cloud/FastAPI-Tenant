"""
JobService — the only interface for enqueueing and managing background jobs.

Routers and business services must use this class; never enqueue directly.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Callable

from rq import Retry
from rq.exceptions import NoSuchJobError
from rq.job import Job

from app.core.config import get_settings
from app.core.rq import get_sync_redis_connection
from app.jobs.job_status import build_job_status_payload, map_rq_status
from app.jobs.queue import QUEUE_DEFAULT, QUEUE_HIGH, QUEUE_LOW, get_queue_by_name

logger = logging.getLogger(__name__)


class JobService:
    """Central interface for background job operations."""

    def __init__(self) -> None:
        settings = get_settings()
        self._retry = Retry(
            max=settings.rq_retry_max,
            interval=settings.rq_retry_interval_list,
        )

    def _execute_sync(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run a task immediately (used in tests via job_sync_mode)."""
        logger.info("Job sync mode: executing %s immediately", func.__name__)
        return func(*args, **kwargs)

    def enqueue(
        self,
        func: Callable[..., Any],
        *args: Any,
        queue_name: str = QUEUE_DEFAULT,
        **kwargs: Any,
    ) -> str:
        """Enqueue a job on the specified queue. Returns job ID."""
        settings = get_settings()
        if settings.job_sync_mode:
            self._execute_sync(func, *args, **kwargs)
            return "sync-mode"

        queue = get_queue_by_name(queue_name)
        job = queue.enqueue(
            func,
            *args,
            **kwargs,
            retry=self._retry,
            result_ttl=settings.rq_result_ttl,
            failure_ttl=settings.rq_failure_ttl,
        )
        logger.info("Job queued: job_id=%s queue=%s func=%s", job.id, queue_name, func.__name__)
        return job.id

    def enqueue_high_priority(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return self.enqueue(func, *args, queue_name=QUEUE_HIGH, **kwargs)

    def enqueue_low_priority(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return self.enqueue(func, *args, queue_name=QUEUE_LOW, **kwargs)

    def enqueue_delayed(
        self,
        func: Callable[..., Any],
        delay: timedelta,
        *args: Any,
        queue_name: str = QUEUE_DEFAULT,
        **kwargs: Any,
    ) -> str:
        """Enqueue a job to run after a delay."""
        settings = get_settings()
        if settings.job_sync_mode:
            self._execute_sync(func, *args, **kwargs)
            return "sync-mode"

        queue = get_queue_by_name(queue_name)
        job = queue.enqueue_in(
            delay,
            func,
            *args,
            **kwargs,
            retry=self._retry,
            result_ttl=settings.rq_result_ttl,
            failure_ttl=settings.rq_failure_ttl,
        )
        logger.info(
            "Job queued (delayed): job_id=%s queue=%s delay=%ss",
            job.id,
            queue_name,
            delay.total_seconds(),
        )
        return job.id

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Fetch job status by ID."""
        if job_id == "sync-mode":
            return {
                "job_id": job_id,
                "status": "finished",
                "queue": QUEUE_DEFAULT,
                "created_at": None,
                "started_at": None,
                "finished_at": None,
                "result": None,
                "error": None,
            }

        try:
            job = Job.fetch(job_id, connection=get_sync_redis_connection())
            return build_job_status_payload(job)
        except NoSuchJobError:
            return None
        except Exception as exc:
            logger.warning("Failed to fetch or decode job_id=%s: %s", job_id, exc)
            return None

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job. Returns True if cancelled."""
        try:
            job = Job.fetch(job_id, connection=get_sync_redis_connection())
        except (NoSuchJobError, Exception) as exc:
            logger.warning("Failed to fetch job for cancellation job_id=%s: %s", job_id, exc)
            return False

        status = map_rq_status(job.get_status())
        if status in {"finished", "failed", "started"}:
            return False

        try:
            job.cancel()
            logger.info("Job cancelled: job_id=%s", job_id)
            return True
        except Exception as exc:
            logger.warning("Failed to cancel job_id=%s: %s", job_id, exc)
            return False

    def retry_job(self, job_id: str) -> bool:
        """Re-queue a failed job."""
        try:
            job = Job.fetch(job_id, connection=get_sync_redis_connection())
        except (NoSuchJobError, Exception) as exc:
            logger.warning("Failed to fetch job for retry job_id=%s: %s", job_id, exc)
            return False

        if map_rq_status(job.get_status()) != "failed":
            return False

        try:
            job.retry()
            logger.info("Retry attempt: job_id=%s", job_id)
            return True
        except Exception as exc:
            logger.warning("Failed to retry job_id=%s: %s", job_id, exc)
            return False


    def list_jobs(
        self,
        *,
        status: str | None = None,
        queue_name: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List jobs across queues, optionally filtered by status."""
        from app.jobs.queue import QUEUE_NAMES

        queues = [get_queue_by_name(queue_name)] if queue_name else [
            get_queue_by_name(name) for name in QUEUE_NAMES
        ]
        jobs: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for queue in queues:
            raw_ids: list[str] = []

            if status is None or status == "queued":
                raw_ids.extend(queue.job_ids[:limit])
            if status is None or status == "started":
                raw_ids.extend(queue.started_job_registry.get_job_ids(0, limit - 1))
            if status is None or status == "finished":
                raw_ids.extend(queue.finished_job_registry.get_job_ids(0, limit - 1))
            if status is None or status == "failed":
                raw_ids.extend(queue.failed_job_registry.get_job_ids(0, limit - 1))

            # Deduplicate while preserving insertion order
            unique_ids = list(dict.fromkeys(raw_ids))

            for job_id in unique_ids:
                if len(jobs) >= limit:
                    break
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                payload = self.get_job(job_id)
                if payload and (status is None or payload["status"] == status):
                    jobs.append(payload)

        return jobs[:limit]

    @staticmethod
    def get_queue_stats() -> dict[str, dict[str, int]]:
        """Return job counts per queue for health checks."""
        from app.jobs.queue import QUEUE_NAMES

        stats: dict[str, dict[str, int]] = {}
        try:
            for name in QUEUE_NAMES:
                queue = get_queue_by_name(name)
                stats[name] = {
                    "queued": len(queue),
                    "started": queue.started_job_registry.count,
                    "finished": queue.finished_job_registry.count,
                    "failed": queue.failed_job_registry.count,
                }
        except Exception as exc:
            logger.warning("Failed to fetch queue stats: %s", exc)
            for name in QUEUE_NAMES:
                stats[name] = {"queued": 0, "started": 0, "finished": 0, "failed": 0}
        return stats

    @staticmethod
    def get_worker_stats() -> dict[str, Any]:
        """Return worker availability for health checks."""
        from rq.worker import Worker

        try:
            connection = get_sync_redis_connection()
            workers = Worker.all(connection=connection)
            return {
                "count": len(workers),
                "status": "running" if workers else "stopped",
                "workers": [
                    {
                        "name": worker.name,
                        "state": worker.get_state(),
                        "queues": [q.name for q in worker.queues],
                    }
                    for worker in workers
                ],
            }
        except Exception as exc:
            logger.warning("Failed to fetch worker stats: %s", exc)
            return {
                "count": 0,
                "status": "stopped",
                "workers": [],
            }

