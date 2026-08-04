"""Run async coroutines from synchronous RQ worker processes."""

import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

T = TypeVar("T")


import logging

logger = logging.getLogger(__name__)

def run_async(coro: Coroutine[Any, Any, T]) -> Any:
    """Execute an async coroutine from a sync worker (or sync-mode tests)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # Already inside a running event loop (e.g. FastAPI request / pytest-asyncio).
    # Defer task execution slightly (100ms) so active request DB transactions commit first.
    def _schedule() -> None:
        try:
            loop.create_task(coro)
        except Exception:
            pass

    loop.call_later(0.1, _schedule)
    return None









