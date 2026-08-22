"""Run async coroutines from synchronous RQ worker processes."""

import asyncio
import concurrent.futures
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


def run_async(coro: Coroutine[Any, Any, T]) -> Any:
    """Execute an async coroutine from a sync worker (or sync-mode tests)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(coro))
            return future.result()

    return asyncio.run(coro)
