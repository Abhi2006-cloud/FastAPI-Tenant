"""
Embedded RQ SimpleWorker daemon thread.

Runs an RQ worker inside the FastAPI process for single-service free tier deployments (Render).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from rq import Queue
from rq.exceptions import DequeueTimeout
from rq.timeouts import TimerDeathPenalty
from rq.utils import now
from rq.worker import SimpleWorker, WorkerStatus

from app.core.config import get_settings
from app.core.rq import get_sync_redis_connection
from app.jobs.queue import get_queue_by_name

logger = logging.getLogger(__name__)


class EmbeddedSimpleWorker(SimpleWorker):
    """
    Subclass of RQ SimpleWorker adapted for running safely inside a background thread:
    - Overrides _install_signal_handlers to avoid ValueError outside main thread.
    - Uses TimerDeathPenalty instead of UnixSignalDeathPenalty (SIGALRM).
    - Checks _stop_requested in dequeue loop for rapid, clean shutdown.
    - Uses configurable dequeue_timeout (default 15s) to balance low Redis chatter and fast shutdown.
    """

    death_penalty_class = TimerDeathPenalty

    def __init__(self, *args: Any, dequeue_timeout: int = 15, **kwargs: Any) -> None:
        self._custom_dequeue_timeout = dequeue_timeout
        super().__init__(*args, **kwargs)

    @property
    def dequeue_timeout(self) -> int:
        return getattr(self, "_custom_dequeue_timeout", 15)

    def _install_signal_handlers(self) -> None:
        """No-op: signals can only be installed in the main thread."""
        pass

    def request_stop(self, signum: Any = None, frame: Any = None) -> None:
        """Signal the embedded worker to stop cleanly."""
        self._stop_requested = True
        self._shutdown_requested_date = now()
        try:
            self.set_shutdown_requested_date()
        except Exception:
            pass
        if self.scheduler:
            self.stop_scheduler()

    def dequeue_job_and_maintain_ttl(
        self, timeout: int | None, max_idle_time: int | None = None
    ) -> tuple[Any, Queue] | None:
        """Override dequeue loop to check self._stop_requested after DequeueTimeout."""
        result = None
        self.set_state(WorkerStatus.IDLE)
        connection_wait_time = 1.0

        while not self._stop_requested:
            try:
                self.heartbeat()
                if self.should_run_maintenance_tasks:
                    self.run_maintenance_tasks()

                result = self.queue_class.dequeue_any(
                    self._ordered_queues,
                    timeout,
                    connection=self.connection,
                    job_class=self.job_class,
                    serializer=self.serializer,
                    death_penalty_class=self.death_penalty_class,
                )
                if result is not None:
                    job, queue = result
                    self.reorder_queues(reference_queue=queue)
                    job.redis_server_version = self.get_redis_server_version()
                break
            except DequeueTimeout:
                if self._stop_requested:
                    break
            except Exception as conn_err:
                logger.error("Embedded worker Redis connection error: %s", conn_err)
                time.sleep(connection_wait_time)
                break

        self.heartbeat()
        return result


class EmbeddedWorkerManager:
    """Manages the lifecycle of the embedded worker daemon thread."""

    _lock = threading.Lock()
    _worker: EmbeddedSimpleWorker | None = None
    _thread: threading.Thread | None = None
    _is_running: bool = False

    @classmethod
    def is_alive(cls) -> bool:
        return bool(cls._thread and cls._thread.is_alive())

    @classmethod
    def get_status(cls) -> dict[str, Any]:
        settings = get_settings()
        if settings.job_sync_mode:
            return {"mode": "sync", "alive": True, "details": "Sync mode active (jobs execute inline)"}
        if not settings.embedded_worker:
            return {"mode": "external", "alive": False, "details": "External worker mode configured"}
        return {
            "mode": "embedded",
            "alive": cls.is_alive(),
            "queues": settings.embedded_worker_queue_list,
        }

    @classmethod
    def start(cls) -> bool:
        """Start the embedded worker in a daemon thread. Guarded against double-start."""
        settings = get_settings()
        if not settings.embedded_worker or settings.job_sync_mode:
            return False

        with cls._lock:
            if cls._is_running and cls._thread and cls._thread.is_alive():
                logger.info("Embedded worker already running; skipping start.")
                return False

            try:
                connection = get_sync_redis_connection()
                queue_names = settings.embedded_worker_queue_list
                queues = [get_queue_by_name(name) for name in queue_names]

                cls._worker = EmbeddedSimpleWorker(queues, connection=connection)
                cls._thread = threading.Thread(
                    target=cls._run_worker,
                    args=(cls._worker,),
                    name="EmbeddedRQWorkerThread",
                    daemon=True,
                )
                cls._is_running = True
                cls._thread.start()
                logger.info(
                    "Embedded RQ worker started in background thread on queues: %s",
                    ", ".join(queue_names),
                )
                return True
            except Exception as exc:
                logger.error("Failed to start embedded RQ worker: %s", exc)
                cls._is_running = False
                return False

    @classmethod
    def _run_worker(cls, worker: EmbeddedSimpleWorker) -> None:
        try:
            worker.work(burst=False)
        except Exception as exc:
            logger.error("Embedded RQ worker crashed: %s", exc)
        finally:
            cls._is_running = False
            logger.info("Embedded RQ worker thread finished.")

    @classmethod
    def stop(cls, timeout: float = 15.0) -> bool:
        """Signal the embedded worker to stop and wait for join."""
        with cls._lock:
            if not cls._is_running and not (cls._thread and cls._thread.is_alive()):
                return True

            logger.info("Stopping embedded RQ worker...")
            if cls._worker:
                cls._worker.request_stop()

            if cls._thread and cls._thread.is_alive():
                cls._thread.join(timeout=timeout)
                if cls._thread.is_alive():
                    logger.warning("Embedded RQ worker thread did not stop within %s seconds", timeout)
                    return False

            cls._is_running = False
            cls._worker = None
            cls._thread = None
            logger.info("Embedded RQ worker stopped successfully.")
            return True

