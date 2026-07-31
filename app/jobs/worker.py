"""
RQ worker entry point.

Run: python -m app.jobs.worker

Listens to default, high, and low priority queues with graceful shutdown.
"""

from __future__ import annotations

import logging
import signal
import sys

from rq import Worker

from app.core.rq import get_sync_redis_connection
from app.jobs.queue import QUEUE_NAMES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    connection = get_sync_redis_connection()
    worker = Worker(QUEUE_NAMES, connection=connection)

    def handle_shutdown(signum: int, _frame: object) -> None:
        logger.info("Worker shutdown signal received: signum=%s", signum)
        worker.request_stop()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

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
