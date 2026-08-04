"""
RQ worker entry point.

Run: python -m app.jobs.worker

Listens to default, high, and low priority queues with graceful shutdown.
Schedules the periodic session cleanup job via RQ Scheduler.
"""

from __future__ import annotations

import os
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

import logging
import signal
import sys
from datetime import timedelta


from rq import Worker

from app.core.config import get_settings
from app.core.rq import get_sync_redis_connection
from app.jobs.queue import QUEUE_NAMES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _schedule_session_cleanup(connection) -> None:
    """
    Register the periodic session cleanup job with the RQ scheduler.

    Uses rq-scheduler's cron or interval approach via the built-in scheduler.
    Gracefully skips if scheduling fails (worker continues running).
    """
    try:
        from rq.job import Job
        from rq import Queue
        from app.jobs.tasks import cleanup_expired_sessions_task

        settings = get_settings()
        interval_hours = settings.session_cleanup_interval_hours
        interval_seconds = interval_hours * 3600

        q = Queue("default", connection=connection)

        # Use RQ scheduler (available via rq >= 1.10 with rq[scheduler])
        # Enqueue with a countdown so it runs after the interval
        # For periodic jobs we rely on the job re-enqueueing itself or RQ Scheduler cron
        try:
            from rq_scheduler import Scheduler  # type: ignore[import]

            scheduler = Scheduler(connection=connection)
            # Cancel any existing cleanup jobs to avoid duplicates
            for job in scheduler.get_jobs():
                if (
                    hasattr(job, "func_name")
                    and "cleanup_expired_sessions" in (job.func_name or "")
                ):
                    scheduler.cancel(job)

            scheduler.schedule(
                scheduled_time=None,  # start now
                func=cleanup_expired_sessions_task,
                interval=interval_seconds,
                repeat=None,  # repeat indefinitely
                queue_name="default",
            )
            logger.info(
                "Session cleanup scheduled every %sh via rq-scheduler", interval_hours
            )
        except ImportError:
            # rq-scheduler not installed — enqueue a one-shot cleanup instead
            logger.info(
                "rq-scheduler not available; enqueueing one-shot session cleanup"
            )
            q.enqueue(cleanup_expired_sessions_task)
    except Exception as exc:
        logger.warning("Failed to schedule session cleanup: %s. Continuing.", exc)


def main() -> None:
    connection = get_sync_redis_connection()
    worker = Worker(QUEUE_NAMES, connection=connection)

    def handle_shutdown(signum: int, _frame: object) -> None:
        logger.info("Worker shutdown signal received: signum=%s", signum)
        worker.request_stop()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Schedule periodic session cleanup
    _schedule_session_cleanup(connection)

    logger.info("Worker started: queues=%s", ", ".join(QUEUE_NAMES))
    try:
        worker.work(with_scheduler=True)
    finally:
        logger.info("Worker stopped")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Worker stopped")
        sys.exit(0)
