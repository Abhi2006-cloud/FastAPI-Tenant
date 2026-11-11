"""
AUDIT MODULE — service.py

Central audit logging service. All modules call create_event() — never
write to audit_logs directly. Read access is org-scoped via membership check.

create_event() enqueues a background job; persist_event() writes directly (worker only).
"""

import csv
import io
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.jobs.tasks import record_audit_event_task
from app.modules.audit.events import AuditAction
from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditFilters, AuditLogRepository
from app.modules.billing.plans import get_plan_limits
from app.modules.organizations.repository import OrganizationRepository
from app.services.job_service import JobService


def sanitize_csv_cell(value: Any) -> str:
    """Neutralize spreadsheet CSV injection (Formula Injection)."""
    if value is None:
        return ""
    val_str = str(value)
    if val_str and val_str[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val_str}"
    return val_str


class AuditLogService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuditLogRepository(db)
        self.job_service = JobService()

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
    ) -> str:
        """Enqueue an audit event for asynchronous persistence.

        In JOB_SYNC_MODE (tests), persist immediately on the request session
        so audit logs remain visible without a worker or separate DB connection.
        """
        if get_settings().job_sync_mode:
            log = await self.persist_event(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=metadata,
            )
            # Enqueue search indexing immediately if search enabled
            if get_settings().is_search_enabled:
                from app.jobs.search_tasks import index_audit_log_task
                self.job_service.enqueue(index_audit_log_task, str(log.id))
            return "sync-mode"


        return self.job_service.enqueue(
            record_audit_event_task,
            str(organization_id),
            str(actor_user_id) if actor_user_id else None,
            action.value,
            resource_type,
            str(resource_id) if resource_id else None,
            metadata,
        )

    async def persist_event(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID | None,
        action: AuditAction,
        resource_type: str,
        resource_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Persist an audit event directly (delegates to worker persistence helper)."""
        from app.modules.audit.worker import persist_audit_event

        return await persist_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
        )

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

        # Plan audit history limitation (free plan bounded by audit_history_days)
        org = await OrganizationRepository(self.db).get_by_id(organization_id)
        limits = get_plan_limits(org.plan if org else "free")
        if limits.audit_history_days:
            cutoff = datetime.now(UTC) - timedelta(days=limits.audit_history_days)
            if start_date is None:
                start_date = cutoff
            else:
                sd = start_date if start_date.tzinfo else start_date.replace(tzinfo=UTC)
                if sd < cutoff:
                    start_date = cutoff

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

    async def export_events_csv(
        self,
        requester_user_id: UUID,
        organization_id: UUID,
        *,
        action: AuditAction | None = None,
        actor_user_id: UUID | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AsyncIterator[str]:
        """G8: Export organization audit events as a streaming CSV with formula injection defense."""
        await self._ensure_member(requester_user_id, organization_id)

        org = await OrganizationRepository(self.db).get_by_id(organization_id)
        limits = get_plan_limits(org.plan if org else "free")
        if limits.audit_history_days:
            cutoff = datetime.now(UTC) - timedelta(days=limits.audit_history_days)
            if start_date is None:
                start_date = cutoff
            else:
                sd = start_date if start_date.tzinfo else start_date.replace(tzinfo=UTC)
                if sd < cutoff:
                    start_date = cutoff

        filters = AuditFilters(
            action=action,
            actor_user_id=actor_user_id,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
        )
        logs = await self.repo.list_for_export(organization_id, filters)

        async def _csv_generator() -> AsyncIterator[str]:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["id", "created_at", "action", "actor_user_id", "resource_type", "resource_id", "metadata"])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

            for item in logs:
                meta_str = json.dumps(item.metadata_) if item.metadata_ else ""
                row = [
                    sanitize_csv_cell(item.id),
                    sanitize_csv_cell(item.created_at.isoformat() if item.created_at else ""),
                    sanitize_csv_cell(item.action.value if hasattr(item.action, "value") else str(item.action)),
                    sanitize_csv_cell(item.actor_user_id),
                    sanitize_csv_cell(item.resource_type),
                    sanitize_csv_cell(item.resource_id),
                    sanitize_csv_cell(meta_str),
                ]
                writer.writerow(row)
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

        return _csv_generator()

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
