"""
AUDIT MODULE — repository.py

All queries are scoped by organization_id for tenant isolation.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.events import AuditAction
from app.modules.audit.models import AuditLog


class AuditFilters:
    """Optional filters for listing audit logs."""

    def __init__(
        self,
        *,
        action: AuditAction | None = None,
        actor_user_id: UUID | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> None:
        self.action = action
        self.actor_user_id = actor_user_id
        self.resource_type = resource_type
        self.start_date = start_date
        self.end_date = end_date


class AuditLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, audit_log: AuditLog) -> AuditLog:
        if audit_log.created_at is None:
            from datetime import UTC, datetime
            audit_log.created_at = datetime.now(UTC)
        self.db.add(audit_log)
        await self.db.flush()
        return audit_log


    def _apply_filters(self, stmt, filters: AuditFilters):
        if filters.action is not None:
            stmt = stmt.where(AuditLog.action == filters.action)
        if filters.actor_user_id is not None:
            stmt = stmt.where(AuditLog.actor_user_id == filters.actor_user_id)
        if filters.resource_type is not None:
            stmt = stmt.where(AuditLog.resource_type == filters.resource_type)
        if filters.start_date is not None:
            stmt = stmt.where(AuditLog.created_at >= filters.start_date)
        if filters.end_date is not None:
            stmt = stmt.where(AuditLog.created_at <= filters.end_date)
        return stmt

    async def list_paginated(
        self,
        organization_id: UUID,
        filters: AuditFilters,
        offset: int,
        limit: int,
    ) -> tuple[list[AuditLog], int]:
        base = select(AuditLog).where(AuditLog.organization_id == organization_id)
        base = self._apply_filters(base, filters)

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        items_stmt = (
            base.order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(items_stmt)
        return list(result.scalars().all()), total

    async def search_paginated(
        self,
        organization_id: UUID,
        *,
        query: str | None,
        action: AuditAction | None,
        resource_type: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[AuditLog], int]:
        base = select(AuditLog).where(AuditLog.organization_id == organization_id)

        if action is not None:
            base = base.where(AuditLog.action == action)
        if resource_type is not None:
            base = base.where(AuditLog.resource_type == resource_type)

        if query:
            pattern = f"%{query}%"
            base = base.where(
                or_(
                    cast(AuditLog.action, String).ilike(pattern),
                    AuditLog.resource_type.ilike(pattern),
                    cast(AuditLog.metadata_, String).ilike(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        items_stmt = (
            base.order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(items_stmt)
        return list(result.scalars().all()), total

    async def list_for_export(
        self, organization_id: UUID, filters: AuditFilters, limit: int = 5000
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        stmt = self._apply_filters(stmt, filters)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
