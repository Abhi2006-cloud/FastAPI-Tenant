"""
AUTH MODULE — auth_audit_repository.py

Database access for AuthAuditLog rows.

Only creates events; audit logs are append-only and never updated.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.auth_audit_model import AuthAuditLog, AuthEventType


class AuthAuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_event(
        self,
        *,
        user_id: UUID | None,
        event_type: AuthEventType,
        session_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict | None = None,
    ) -> AuthAuditLog:
        """Append a new authentication audit event."""
        log = AuthAuditLog(
            user_id=user_id,
            event_type=event_type,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_=metadata,
        )
        self.db.add(log)
        await self.db.flush()
        return log
