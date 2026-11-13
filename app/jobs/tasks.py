"""
RQ worker tasks.

Workers execute these functions. Each task delegates to the service layer
via async database sessions — no business logic lives here.
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from app.core.config import get_settings
from app.core.database import worker_session_factory as async_session_factory
from app.jobs.async_runner import run_async

# Ensure all SQLAlchemy ORM models are registered in worker process
from app.modules.auth.models import User  # noqa: F401
from app.modules.auth.session_model import UserSession  # noqa: F401
from app.modules.auth.auth_audit_model import AuthAuditLog  # noqa: F401
from app.modules.organizations.models import Organization  # noqa: F401
from app.modules.memberships.models import Membership  # noqa: F401
from app.modules.files.models import FileRecord  # noqa: F401
from app.modules.audit.models import AuditLog  # noqa: F401
from app.modules.invitations.models import Invitation  # noqa: F401
from app.modules.search.models import SearchIndexFailure  # noqa: F401
from app.modules.email.models import EmailLog  # noqa: F401
from app.jobs.email_tasks import process_email_job_task  # noqa: F401


from app.modules.audit.events import AuditAction
from app.modules.audit.worker import persist_audit_event
from app.modules.files.repository import FileRepository
from app.modules.files.storage import StorageService


logger = logging.getLogger(__name__)
settings = get_settings()


async def _persist_audit_event(

    organization_id: str,
    actor_user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    async with async_session_factory() as session:
        try:
            audit_log = await persist_audit_event(
                session,
                organization_id=UUID(organization_id),
                actor_user_id=UUID(actor_user_id) if actor_user_id else None,
                action=AuditAction(action),
                resource_type=resource_type,
                resource_id=UUID(resource_id) if resource_id else None,
                metadata=metadata,
            )
            await session.commit()
            return {"audit_log_id": str(audit_log.id)}
        except Exception as exc:
            await session.rollback()
            # If the organization was already deleted before this background task ran,
            # ignore foreign key constraint violation gracefully.
            if "audit_logs_organization_id_fkey" in str(exc) or "ForeignKeyViolationError" in type(exc).__name__:
                logger.warning(
                    "Skipping audit event '%s' for deleted organization %s: %s",
                    action,
                    organization_id,
                    exc,
                )
                return {"status": "skipped", "reason": "organization_deleted"}
            raise


def record_audit_event_task(
    organization_id: str,
    actor_user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Persist an audit log entry (executed by worker)."""
    logger.info("Job started: record_audit_event action=%s org=%s", action, organization_id)
    try:
        result = run_async(
            _persist_audit_event(
                organization_id,
                actor_user_id,
                action,
                resource_type,
                resource_id,
                metadata,
            )
        )
        logger.info("Job completed: record_audit_event audit_log_id=%s", result["audit_log_id"])
        
        # Enqueue search indexing task for the persisted audit log
        from app.services.job_service import JobService
        if settings.is_search_enabled:
            from app.jobs.search_tasks import index_audit_log_task
            JobService().enqueue(index_audit_log_task, result["audit_log_id"])
        
        return result
    except Exception as exc:
        logger.exception("Job failed: record_audit_event: %s", exc)
        raise


async def _process_file_upload(file_id: str, organization_id: str) -> dict:
    async with async_session_factory() as session:
        repo = FileRepository(session)
        record = await repo.get_by_id(UUID(file_id))
        if record is None:
            raise ValueError(f"File not found: {file_id}")
        if str(record.organization_id) != organization_id:
            raise ValueError("File does not belong to organization")

        storage = StorageService(Path(settings.upload_dir), db=session)
        on_disk = await storage.async_exists(record.file_path)

        metadata = {
            "file_id": str(record.id),
            "organization_id": organization_id,
            "file_name": record.file_name,
            "file_size": record.file_size,
            "file_path": record.file_path,
            "uploaded_by": str(record.uploaded_by),
            "on_disk": on_disk,
        }
        await session.commit()
        return metadata


def process_file_upload_task(file_id: str, organization_id: str) -> dict:
    """Post-upload processing hook for background metadata extraction, indexing, or verification."""
    logger.info("Job started: process_file_upload file_id=%s", file_id)
    try:
        result = run_async(_process_file_upload(file_id, organization_id))
        logger.info("Job completed: process_file_upload file_id=%s", file_id)
        return result
    except Exception as exc:
        logger.exception("Job failed: process_file_upload: %s", exc)
        raise


# Export search tasks so they are discoverable under app.jobs.tasks
from app.jobs.search_tasks import (
    index_organization_task,
    delete_organization_task,
    index_member_task,
    delete_member_task,
    index_file_task,
    delete_file_task,
    index_audit_log_task
)


# ── Session Cleanup Task ─────────────────────────────────────────────────────

async def _cleanup_expired_sessions() -> dict:
    """Delete expired user sessions from the database."""
    from app.modules.auth.session_repository import SessionRepository

    async with async_session_factory() as session:
        try:
            repo = SessionRepository(session)
            deleted = await repo.delete_expired()
            await session.commit()
            return {"deleted_sessions": deleted}
        except Exception:
            await session.rollback()
            raise


def cleanup_expired_sessions_task() -> dict:
    """Periodic RQ task: delete expired sessions. Run every SESSION_CLEANUP_INTERVAL_HOURS."""
    logger.info("Job started: cleanup_expired_sessions")
    try:
        result = run_async(_cleanup_expired_sessions())
        logger.info(
            "Job completed: cleanup_expired_sessions deleted=%s",
            result.get("deleted_sessions", 0),
        )
        return result
    except Exception as exc:
        logger.exception("Job failed: cleanup_expired_sessions: %s", exc)
        raise
