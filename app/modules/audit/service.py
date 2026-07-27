"""
AUDIT MODULE — service.py

Central audit logging service. All modules call create_event() — never
write to audit_logs directly. Read access is org-scoped via membership check.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.events import AuditAction
from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditFilters, AuditLogRepository


class AuditLogService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuditLogRepository(db)

    async def _ensure_member(self, requester_user_id: UUID, organization_id: UUID) -> None:
        """Lazy import avoids circular dependency with memberships.service."""
        from app.modules.memberships.service import MembershipService

        await MembershipService(self.db).ensure_member(requester_user_id, organization_id)

    async def create_event(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID | None,
        action: AuditAction,
        resource_type: str,
        resource_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Record an audit event. Called by business services after successful operations."""
        audit_log = AuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_=metadata or {},
        )
        return await self.repo.create(audit_log)

    async def list_events(
        self,
        requester_user_id: UUID,
        organization_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        action: AuditAction | None = None,
        actor_user_id: UUID | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[AuditLog], int]:
        """
        List audit events for an organization (newest first).

        All members (owner, admin, member) have read access.
        """
        await self._ensure_member(requester_user_id, organization_id)

        filters = AuditFilters(
            action=action,
            actor_user_id=actor_user_id,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
        )
        offset = (page - 1) * page_size
        return await self.repo.list_paginated(
            organization_id, filters, offset, page_size
        )

    async def search_events(
        self,
        requester_user_id: UUID,
        organization_id: UUID,
        *,
        query: str | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AuditLog], int]:
        """
        Search audit events by action, resource type, or metadata text.

        PostgreSQL-friendly ILIKE on JSON cast; works on SQLite for tests.
        """
        await self._ensure_member(requester_user_id, organization_id)

        offset = (page - 1) * page_size
        return await self.repo.search_paginated(
            organization_id,
            query=query,
            action=action,
            resource_type=resource_type,
            offset=offset,
            limit=page_size,
        )
