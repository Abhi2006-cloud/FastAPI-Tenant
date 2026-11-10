"""
Jobs API — job status and listing scoped by organization.

Routers only expose HTTP; enqueueing happens in services via JobService.
Requires authenticated user with OWNER or ADMIN role in the active organization.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import (
    get_current_membership,
    get_current_user,
    get_organization_id_header,
    require_roles,
)
from app.modules.auth.models import User
from app.modules.memberships.models import Membership, MembershipRole
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    _: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    __: Annotated[Membership, Depends(require_roles(MembershipRole.OWNER, MembershipRole.ADMIN))],
) -> dict:
    """Return status and metadata for a background job scoped to the active organization."""
    job = JobService().get_job(job_id, organization_id=str(organization_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("")
async def list_jobs(
    _: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    __: Annotated[Membership, Depends(require_roles(MembershipRole.OWNER, MembershipRole.ADMIN))],
    status: str | None = Query(None, description="Filter: queued, started, finished, failed"),
    queue: str | None = Query(None, description="Filter by queue name"),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List background jobs for the active organization's admin dashboard."""
    jobs = JobService().list_jobs(
        status=status,
        queue_name=queue,
        organization_id=str(organization_id),
        limit=limit,
    )
    return {"items": jobs, "total": len(jobs)}
