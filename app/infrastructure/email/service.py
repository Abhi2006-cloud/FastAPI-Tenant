"""EmailService — Unified entry point for all email operations, template rendering, and background job enqueueing."""

import logging
import time
from datetime import UTC, datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import RedisClient
from app.infrastructure.email.client import get_email_provider
from app.infrastructure.email.exceptions import EmailRateLimitException
from app.infrastructure.email.health import check_email_health
from app.infrastructure.email.renderer import email_renderer
from app.infrastructure.email.templates import TEMPLATE_INVITATION
from app.jobs.queue import QUEUE_EMAIL
from app.modules.email.models import EmailLog, EmailStatus
from app.modules.email.repository import EmailLogRepository
from app.services.job_service import JobService

logger = logging.getLogger(__name__)


class EmailService:
    """Central service managing email creation, template rendering, rate limiting, and background enqueueing."""

    def __init__(self, db: Optional[AsyncSession] = None) -> None:
        self.db = db
        self.job_service = JobService()

    async def check_rate_limit(self, organization_id: UUID) -> None:
        """Enforce Redis rate limit (default 20 invites per org per hour)."""
        settings = get_settings()
        limit = settings.email_rate_limit_per_hour
        current_hour = int(time.time() // 3600)
        key = f"ratelimit:invite:{organization_id}:{current_hour}"

        try:
            client = await RedisClient.get_client()
            count = await client.incr(key)
            if count == 1:
                # Set TTL for 1 hour window
                await client.expire(key, 3600)

            if count > limit:
                logger.warning(
                    "Organization %s exceeded invitation rate limit (%s/hr)",
                    organization_id, limit
                )
                raise EmailRateLimitException(
                    f"Invitation rate limit exceeded. Maximum {limit} invitations per hour allowed."
                )
        except EmailRateLimitException:
            raise
        except Exception as exc:
            logger.warning("Redis rate limit check bypassed due to error: %s", exc)

    async def queue_email(
        self,
        *,
        recipient_email: str,
        template_name: str,
        subject: str,
        context: Dict[str, Any],
        organization_id: Optional[UUID] = None,
    ) -> EmailLog:
        """Create an EmailLog record in database and enqueue job to dedicated 'email' queue."""
        if not self.db:
            raise RuntimeError("Database session required for queue_email operations.")

        settings = get_settings()
        provider = get_email_provider()

        repo = EmailLogRepository(self.db)
        email_log = EmailLog(
            organization_id=organization_id,
            recipient_email=recipient_email,
            provider=provider.name,
            template_name=template_name,
            subject=subject,
            status=EmailStatus.QUEUED,
            metadata_={"context": context},
        )
        created_log = await repo.create(email_log)
        await self.db.commit()

        # Import task lazily to prevent circular imports

        from app.jobs.email_tasks import process_email_job_task

        rq_job_id = self.job_service.enqueue(
            process_email_job_task,
            str(created_log.id),
            queue_name=QUEUE_EMAIL,
        )

        created_log.rq_job_id = rq_job_id
        await repo.update(created_log)
        logger.info(
            "Email queued. Log ID: %s, RQ Job ID: %s, Recipient: %s, Template: %s",
            created_log.id, rq_job_id, recipient_email, template_name
        )
        return created_log

    async def send_invitation(
        self,
        *,
        organization_id: UUID,
        organization_name: str,
        inviter_name: str,
        recipient_email: str,
        invitation_token: str,
        expire_hours: int = 72,
    ) -> EmailLog:
        """Build invitation link, enforce rate limit, and enqueue invitation email job."""
        await self.check_rate_limit(organization_id)

        settings = get_settings()
        join_url = f"{settings.frontend_url}/invitations?token={invitation_token}"

        context = {
            "organization_name": organization_name,
            "inviter_name": inviter_name,
            "recipient_email": recipient_email,
            "join_url": join_url,
            "expire_hours": expire_hours,
            "company_name": settings.app_name,
            "support_email": settings.email_from_address,
        }

        subject = f"You've been invited to join {organization_name}"
        return await self.queue_email(
            recipient_email=recipient_email,
            template_name=TEMPLATE_INVITATION,
            subject=subject,
            context=context,
            organization_id=organization_id,
        )

    async def send_email_direct(
        self,
        *,
        to: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> Dict[str, Any]:
        """Send email synchronously using active provider (useful for test calls)."""
        provider = get_email_provider()
        return await provider.send_email(
            to=to,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def retry_email(
        self, email_log_id: UUID, organization_id: Optional[UUID] = None
    ) -> Optional[EmailLog]:
        """Re-queue a failed EmailLog entry, verifying organization ownership."""
        if not self.db:
            raise RuntimeError("Database session required for retry_email.")

        repo = EmailLogRepository(self.db)
        log = await repo.get_by_id(email_log_id)
        if not log:
            return None

        # Enforce organization ownership if specified
        if organization_id is not None and log.organization_id != organization_id:
            logger.warning(
                "Cross-tenant email retry rejected. Log org: %s, Request org: %s",
                log.organization_id,
                organization_id,
            )
            return None

        if log.status not in (EmailStatus.FAILED, EmailStatus.CANCELLED):
            logger.warning("EmailLog %s status is %s; cannot retry.", email_log_id, log.status)
            return log

        log.status = EmailStatus.QUEUED
        log.error_message = None

        from app.jobs.email_tasks import process_email_job_task

        rq_job_id = self.job_service.enqueue(
            process_email_job_task,
            str(log.id),
            queue_name=QUEUE_EMAIL,
        )
        log.rq_job_id = rq_job_id
        return await repo.update(log)

    async def check_health(self) -> Dict[str, Any]:
        """Return provider health status (cached 60s)."""
        return await check_email_health()
