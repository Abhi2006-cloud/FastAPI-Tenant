"""
Jobs API — job status and listing.

Routers only expose HTTP; enqueueing happens in services via JobService.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    _: User = Depends(get_current_user),
) -> dict:
    """Return status and metadata for a background job."""
    job = JobService().get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("")
async def list_jobs(
    status: str | None = Query(None, description="Filter: queued, started, finished, failed"),
    queue: str | None = Query(None, description="Filter by queue name"),
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(get_current_user),
) -> dict:
    """List background jobs for the admin dashboard."""
    jobs = JobService().list_jobs(status=status, queue_name=queue, limit=limit)
    return {"items": jobs, "total": len(jobs)}
