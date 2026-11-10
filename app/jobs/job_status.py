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


def _sanitize_result(val: Any) -> Any:
    """Mask sensitive keys in job results to prevent credential or secret leakage."""
    if isinstance(val, dict):
        sanitized = {}
        for k, v in val.items():
            if any(s in str(k).lower() for s in ("token", "password", "secret", "key", "credential")):
                sanitized[k] = "***"
            else:
                sanitized[k] = _sanitize_result(v)
        return sanitized
    if isinstance(val, (list, tuple)):
        return [_sanitize_result(item) for item in val]
    return val


def build_job_status_payload(job: Job) -> dict[str, Any]:
    """Build a serializable job status dict from an RQ Job without leaking internal traces."""
    status = map_rq_status(job.get_status())
    raw_result = job.result if status == "finished" else None
    
    payload: dict[str, Any] = {
        "job_id": job.id,
        "status": status,
        "queue": job.origin or "default",
        "created_at": _to_iso(job.created_at),
        "started_at": _to_iso(job.started_at),
        "finished_at": _to_iso(job.ended_at),
        "result": _make_serializable(_sanitize_result(raw_result)),
        "error": None,
    }

    if status == "failed":
        # Extract only the summary exception message without stack frames, file paths, or local variables
        err_val = "Job execution failed"
        if job.exc_info:
            lines = [l.strip() for l in job.exc_info.strip().splitlines() if l.strip()]
            if lines:
                err_val = lines[-1]
        elif job.result is not None:
            err_val = str(job.result)
        payload["error"] = _make_serializable(err_val)

    return payload

