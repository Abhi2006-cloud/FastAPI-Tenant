"""EMAIL MODULE — router.py

Management endpoints for email monitoring, log inspection, retries, and test emails.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.infrastructure.email.client import get_email_provider
from app.infrastructure.email.service import EmailService
from app.modules.auth.models import User
from app.modules.email.models import EmailStatus
from app.modules.email.repository import EmailLogRepository
from app.modules.email.schemas import (
    EmailLogListResponse,
    EmailLogResponse,
    EmailStatsResponse,
    SendTestEmailRequest,
)

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/test", response_model=EmailLogResponse, status_code=status.HTTP_201_CREATED)
async def send_test_email(
    data: SendTestEmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EmailLogResponse:
    """Send a test email using the configured email infrastructure."""
    service = EmailService(db)
    context = data.context or {"user_name": current_user.email}
    log = await service.queue_email(
        recipient_email=data.to_email,
        template_name=data.template_name,
        subject=data.subject,
        context=context,
    )
    return EmailLogResponse.model_validate(log)


@router.get("/logs", response_model=EmailLogListResponse)
async def list_email_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    org_id: Optional[UUID] = Query(None, description="Filter by organization ID"),
    status: Optional[EmailStatus] = Query(None, description="Filter by email status"),
    recipient: Optional[str] = Query(None, description="Filter by recipient email"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> EmailLogListResponse:
    """List email logs with optional filtering and pagination."""
    repo = EmailLogRepository(db)
    logs, total = await repo.list_logs(
        organization_id=org_id,
        status=status,
        recipient_email=recipient,
        limit=limit,
        offset=offset,
    )
    return EmailLogListResponse(
        logs=[EmailLogResponse.model_validate(l) for l in logs],
        total=total,
    )


@router.post("/logs/{log_id}/retry", response_model=EmailLogResponse)
async def retry_email(
    log_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EmailLogResponse:
    """Manually retry a failed email log entry."""
    service = EmailService(db)
    log = await service.retry_email(log_id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email log not found")
    return EmailLogResponse.model_validate(log)


@router.get("/stats", response_model=EmailStatsResponse)
async def get_email_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    org_id: Optional[UUID] = Query(None, description="Filter by organization ID"),
) -> EmailStatsResponse:
    """Get delivery statistics and email health status."""
    repo = EmailLogRepository(db)
    stats = await repo.get_stats(organization_id=org_id)

    provider = get_email_provider()
    service = EmailService(db)
    health = await service.check_health()

    return EmailStatsResponse(
        total_emails=stats["total_emails"],
        status_counts=stats["status_counts"],
        success_rate_percent=stats["success_rate_percent"],
        active_provider=provider.name,
        health_status=health,
    )
