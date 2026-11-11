"""
AUDIT MODULE — router.py

  GET /audit-logs         — list with pagination and filters
  GET /audit-logs/search  — search by action, resource type, metadata

Requires JWT + X-Organization-Id + organization membership.
All roles (owner, admin, member) have read access.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_membership,
    get_current_user,
    get_organization_id_header,
    require_feature,
)
from app.modules.audit.events import AuditAction
from app.modules.audit.schemas import AuditLogListResponse, AuditLogResponse, AuditLogSearchResponse
from app.modules.audit.service import AuditLogService
from app.modules.auth.models import User
from app.modules.memberships.models import Membership

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    _: Annotated[Membership, Depends(get_current_membership)],
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    action: AuditAction | None = Query(None, description="Filter by action type"),
    actor_user_id: UUID | None = Query(None, description="Filter by actor user ID"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    start_date: datetime | None = Query(None, description="Filter events on or after this UTC datetime"),
    end_date: datetime | None = Query(None, description="Filter events on or before this UTC datetime"),
) -> AuditLogListResponse:
    """List organization audit logs, newest first."""
    service = AuditLogService(db)
    items, total = await service.list_events(
        current_user.id,
        organization_id,
        page=page,
        page_size=page_size,
        action=action,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/export")
async def export_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    _: Annotated[Membership, Depends(get_current_membership)],
    __: Annotated[None, Depends(require_feature("audit_export"))],
    action: AuditAction | None = Query(None, description="Filter by action type"),
    actor_user_id: UUID | None = Query(None, description="Filter by actor user ID"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    start_date: datetime | None = Query(None, description="Filter events on or after this UTC datetime"),
    end_date: datetime | None = Query(None, description="Filter events on or before this UTC datetime"),
) -> StreamingResponse:
    """G8: Export organization audit logs as streaming CSV. Requires audit_export plan feature."""
    service = AuditLogService(db)
    csv_stream = await service.export_events_csv(
        current_user.id,
        organization_id,
        action=action,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
    )
    return StreamingResponse(
        csv_stream,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="audit_logs_{organization_id}.csv"'},
    )


@router.get("/search", response_model=AuditLogSearchResponse)
async def search_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    _: Annotated[Membership, Depends(get_current_membership)],
    q: str | None = Query(None, min_length=1, description="Search action, resource type, or metadata"),
    action: AuditAction | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> AuditLogSearchResponse:
    """Search audit logs by action, resource type, or metadata content."""
    service = AuditLogService(db)
    items, total = await service.search_events(
        current_user.id,
        organization_id,
        query=q,
        action=action,
        resource_type=resource_type,
        page=page,
        page_size=page_size,
    )
    return AuditLogSearchResponse(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        query=q,
    )
