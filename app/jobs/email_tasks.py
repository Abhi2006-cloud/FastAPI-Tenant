"""Background RQ tasks for email delivery processing."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import worker_session_factory as async_session_factory
from app.infrastructure.email.client import get_email_provider
from app.infrastructure.email.renderer import email_renderer
from app.modules.email.models import EmailStatus
from app.modules.email.repository import EmailLogRepository

# Ensure all SQLAlchemy ORM models are registered in worker process
from app.models import (  # noqa: F401
    AuditLog,
    EmailLog,
    FileRecord,
    Invitation,
    Membership,
    Organization,
    SearchIndexFailure,
    User,
)

from app.jobs.async_runner import run_async

logger = logging.getLogger(__name__)

# Exponential backoff retry delays in seconds (Retry 1: 30s, Retry 2: 2m, Retry 3: 10m, Retry 4: 30m, Retry 5: 1h)
EXPONENTIAL_RETRY_DELAYS = [30, 120, 600, 1800, 3600]



def process_email_job_task(email_log_id: str) -> dict:
    """RQ Worker entry point. Payload optimized to receive only email_log_id string."""
    logger.info("Executing process_email_job_task for EmailLog ID: %s", email_log_id)
    return run_async(_process_email_job(UUID(email_log_id)))


async def _process_email_job(log_id: UUID, session: Optional[AsyncSession] = None) -> dict:
    """Async implementation of email task execution."""
    if session:
        return await _process_email_job_with_session(log_id, session)

    async with async_session_factory() as db:
        return await _process_email_job_with_session(log_id, db)


async def _process_email_job_with_session(log_id: UUID, session: AsyncSession) -> dict:
    repo = EmailLogRepository(session)
    email_log = await repo.get_by_id(log_id)

    if not email_log:
        logger.error("EmailLog record not found for ID: %s", log_id)
        return {"status": "not_found", "email_log_id": str(log_id)}

    if email_log.status in (EmailStatus.SENT, EmailStatus.CANCELLED):
        logger.info("EmailLog %s is already %s. Skipping.", log_id, email_log.status)
        return {"status": "skipped", "email_log_id": str(log_id)}

    # Update status to PROCESSING
    email_log.status = EmailStatus.PROCESSING
    await repo.update(email_log)

    settings = get_settings()
    provider = get_email_provider()

    context = {}
    if email_log.metadata_ and isinstance(email_log.metadata_, dict):
        context = email_log.metadata_.get("context", {})

    try:
        # Render HTML and Plain Text
        html_content, text_content = email_renderer.render(
            email_log.template_name, context
        )

        # Send via active provider
        res = await provider.send_email(
            to=email_log.recipient_email,
            subject=email_log.subject,
            html_content=html_content,
            text_content=text_content,
        )

        # Update status to SENT
        email_log.status = EmailStatus.SENT
        email_log.sent_at = datetime.now(UTC)
        email_log.provider_message_id = str(res.get("id") or res.get("message_id", ""))
        email_log.error_message = None
        await repo.update(email_log)

        logger.info(
            "Email delivery succeeded for EmailLog %s (Recipient: %s, Message ID: %s)",
            log_id, email_log.recipient_email, email_log.provider_message_id
        )
        return {
            "status": "sent",
            "email_log_id": str(log_id),
            "message_id": email_log.provider_message_id,
        }

    except Exception as exc:
        error_msg = str(exc)
        logger.error("Email delivery failed for EmailLog %s: %s", log_id, error_msg)

        email_log.retry_count += 1
        max_retries = settings.email_max_retries

        if email_log.retry_count < max_retries:
            email_log.status = EmailStatus.QUEUED
            email_log.error_message = f"Retry {email_log.retry_count}/{max_retries} failed: {error_msg}"
            await repo.update(email_log)

            delay_index = min(email_log.retry_count - 1, len(EXPONENTIAL_RETRY_DELAYS) - 1)
            retry_delay = EXPONENTIAL_RETRY_DELAYS[delay_index]

            logger.info(
                "Re-queueing EmailLog %s for retry %s/%s in %s seconds",
                log_id, email_log.retry_count, max_retries, retry_delay
            )
        else:
            email_log.status = EmailStatus.FAILED
            email_log.failed_at = datetime.now(UTC)
            email_log.error_message = f"Final failure after {email_log.retry_count} retries: {error_msg}"
            await repo.update(email_log)
            logger.error("EmailLog %s permanently marked as FAILED.", log_id)

        return {
            "status": email_log.status.value,
            "email_log_id": str(log_id),
            "error": error_msg,
            "retry_count": email_log.retry_count,
        }


def new_device_login_email_task(user_id: str, recipient_email: str, context: dict) -> dict:
    """RQ task entry point for enqueueing new device login notifications."""
    logger.info("Executing new_device_login_email_task for user %s (%s)", user_id, recipient_email)
    return run_async(_new_device_login_email(user_id, recipient_email, context))


async def _new_device_login_email(user_id: str, recipient_email: str, context: dict) -> dict:
    from app.infrastructure.email.service import EmailService
    try:
        async with async_session_factory() as db:
            svc = EmailService(db)
            log = await svc.queue_email(
                recipient_email=recipient_email,
                subject=f"New login detected on {context.get('device_name') or 'a new device'}",
                template_name="new_device_login",
                context=context,
            )
            return {"status": "queued", "email_log_id": str(log.id) if log else None}
    except Exception as exc:
        logger.warning("Failed to queue new device login email: %s", exc)
        return {"status": "error", "error": str(exc)}


