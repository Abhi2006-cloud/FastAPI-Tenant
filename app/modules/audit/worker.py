"""
Audit persistence for background workers.

Separated from AuditLogService to avoid circular imports between
service layer and RQ task modules.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.events import AuditAction
from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditLogRepository


async def persist_audit_event(
    session: AsyncSession,
    *,
    organization_id: UUID,
    actor_user_id: UUID | None,
    action: AuditAction,
    resource_type: str,
    resource_id: UUID | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    """Write an audit log entry directly (worker use only)."""
    audit_log = AuditLog(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_=metadata or {},
    )
    return await AuditLogRepository(session).create(audit_log)
