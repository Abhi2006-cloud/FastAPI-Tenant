"""Run async coroutines from synchronous RQ worker processes."""

import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

T = TypeVar("T")


async def _execute_with_cleanup(coro: Coroutine[Any, Any, T]) -> T:
    try:
        return await coro
    finally:
        from app.core.database import engine
        await engine.dispose()


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Execute an async coroutine from a sync worker (or sync-mode tests)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_execute_with_cleanup(coro))

    # Already inside an event loop (e.g. FastAPI request / pytest-asyncio).
    # Run the coroutine in a dedicated thread with its own loop.
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _execute_with_cleanup(coro)).result()

