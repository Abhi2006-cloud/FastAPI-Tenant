"""
RQ queue definitions.

Centralizes queue names so services never construct queues directly.
"""

from enum import Enum

from rq import Queue

from app.core.rq import get_queue

QUEUE_DEFAULT = "default"
QUEUE_HIGH = "high"
QUEUE_LOW = "low"

QUEUE_NAMES = (QUEUE_DEFAULT, QUEUE_HIGH, QUEUE_LOW)


class QueuePriority(str, Enum):
    DEFAULT = QUEUE_DEFAULT
    HIGH = QUEUE_HIGH
    LOW = QUEUE_LOW


def get_default_queue() -> Queue:
    return get_queue(QUEUE_DEFAULT)


def get_high_priority_queue() -> Queue:
    return get_queue(QUEUE_HIGH)


def get_low_priority_queue() -> Queue:
    return get_queue(QUEUE_LOW)


def get_queue_by_name(name: str) -> Queue:
    if name not in QUEUE_NAMES:
        raise ValueError(f"Unknown queue: {name}")
    return get_queue(name)
