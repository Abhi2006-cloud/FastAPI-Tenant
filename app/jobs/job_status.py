"""
Map RQ job states to API-facing status values and build response payloads.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rq.job import Job

RQ_STATUS_MAP: dict[str, str] = {
    "queued": "queued",
    "deferred": "queued",
    "scheduled": "queued",
    "started": "started",
    "finished": "finished",
    "failed": "failed",
    "stopped": "failed",
    "canceled": "failed",
}


def map_rq_status(rq_status: str | None) -> str:
    if not rq_status:
        return "unknown"
    return RQ_STATUS_MAP.get(rq_status, rq_status)


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _make_serializable(val: Any) -> Any:
    """Ensure value can be safely serialized to JSON."""
    if val is None or isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, (list, tuple)):
        return [_make_serializable(item) for item in val]
    if isinstance(val, dict):
        return {str(k): _make_serializable(v) for k, v in val.items()}
    if isinstance(val, Exception):
        return str(val)
    return str(val)


def build_job_status_payload(job: Job) -> dict[str, Any]:
    """Build a serializable job status dict from an RQ Job."""
    status = map_rq_status(job.get_status())
    raw_result = job.result if status == "finished" else None
    
    payload: dict[str, Any] = {
        "job_id": job.id,
        "status": status,
        "queue": job.origin or "default",
        "created_at": _to_iso(job.created_at),
        "started_at": _to_iso(job.started_at),
        "finished_at": _to_iso(job.ended_at),
        "result": _make_serializable(raw_result),
        "error": None,
    }

    if status == "failed":
        err_val = job.exc_info or (str(job.result) if job.result is not None else "Job failed")
        payload["error"] = _make_serializable(err_val)

    return payload

