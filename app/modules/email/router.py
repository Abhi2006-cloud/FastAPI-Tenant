"""EMAIL MODULE — router.py

Management endpoints for email monitoring, log inspection, retries, and test emails.
Requires authenticated user with OWNER or ADMIN role in the active organization.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import (
    get_current_membership,
    get_current_user,
    get_organization_id_header,
    require_platform_admin,
    require_roles,
)
from app.infrastructure.email.client import get_email_provider
from app.infrastructure.email.service import EmailService
from app.modules.auth.models import User
from app.modules.email.models import EmailLog, EmailStatus
from app.modules.email.repository import EmailLogRepository
from app.modules.email.schemas import (
    EmailLogListResponse,
    EmailLogResponse,
    EmailStatsResponse,
    SendTestEmailRequest,
)
from app.modules.memberships.models import Membership, MembershipRole

router = APIRouter(prefix="/email", tags=["email"])


def _sanitize_email_log(log: EmailLog) -> EmailLog:
    """Sanitize metadata in EmailLog so invitation tokens or secrets are not leaked."""
    settings = get_settings()
    if not settings.expose_invitation_tokens and log.metadata_:
        meta = dict(log.metadata_)
        if "context" in meta and isinstance(meta["context"], dict):
            ctx = dict(meta["context"])
            if "join_url" in ctx:
                ctx["join_url"] = "***"
            if "invitation_token" in ctx:
                ctx["invitation_token"] = "***"
            meta["context"] = ctx
            log.metadata_ = meta
    return log


@router.post("/test", response_model=EmailLogResponse, status_code=status.HTTP_201_CREATED)
async def send_test_email(
    data: SendTestEmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_platform_admin)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    _: Annotated[Membership, Depends(require_roles(MembershipRole.OWNER, MembershipRole.ADMIN))],
) -> EmailLogResponse:
    """Send a test email using the configured email infrastructure.
    
    Restricted to OWNER/ADMIN in development/testing mode; disabled in production.
    """
    settings = get_settings()
    if settings.is_production_email_enabled or settings.email_mode.lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test email sending is disabled in production.",
        )
    service = EmailService(db)
    context = data.context or {"user_name": current_user.email}
    log = await service.queue_email(
        recipient_email=data.to_email,
        template_name=data.template_name,
        subject=data.subject,
        context=context,
        organization_id=organization_id,
    )
    return EmailLogResponse.model_validate(_sanitize_email_log(log))


@router.get("/logs", response_model=EmailLogListResponse)
async def list_email_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    __: Annotated[Membership, Depends(require_roles(MembershipRole.OWNER, MembershipRole.ADMIN))],
    status: Optional[EmailStatus] = Query(None, description="Filter by email status"),
    recipient: Optional[str] = Query(None, description="Filter by recipient email"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> EmailLogListResponse:
    """List email logs strictly scoped to the active organization."""
    repo = EmailLogRepository(db)
    logs, total = await repo.list_logs(
        organization_id=organization_id,
        status=status,
        recipient_email=recipient,
        limit=limit,
        offset=offset,
    )
    return EmailLogListResponse(
        logs=[EmailLogResponse.model_validate(_sanitize_email_log(l)) for l in logs],
        total=total,
    )


@router.post("/logs/{log_id}/retry", response_model=EmailLogResponse)
async def retry_email(
    log_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    __: Annotated[Membership, Depends(require_roles(MembershipRole.OWNER, MembershipRole.ADMIN))],
) -> EmailLogResponse:
    """Manually retry a failed email log entry belonging to the active organization."""
    service = EmailService(db)
    log = await service.retry_email(log_id, organization_id=organization_id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email log not found")
    return EmailLogResponse.model_validate(_sanitize_email_log(log))


@router.get("/stats", response_model=EmailStatsResponse)
async def get_email_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    __: Annotated[Membership, Depends(require_roles(MembershipRole.OWNER, MembershipRole.ADMIN))],
) -> EmailStatsResponse:
    """Get delivery statistics and email health status for the active organization."""
    repo = EmailLogRepository(db)
    stats = await repo.get_stats(organization_id=organization_id)

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
