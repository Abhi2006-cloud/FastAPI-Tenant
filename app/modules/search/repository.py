"""
SEARCH MODULE — repository.py

Database repository for tenant-scoped basic search queries over Postgres / SQLite.
Layering: router -> service -> repository.
Every query filters strictly by organization_id.
"""

from typing import Any, Dict, List, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.files.models import FileRecord
from app.modules.memberships.models import Membership


class BasicSearchRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _sanitize_like(term: str) -> str:
        escaped = term.lower().replace("%", "")
        return f"%{escaped}%"

    async def search_files(
        self, organization_id: UUID, query: str, limit: int, offset: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        pattern = self._sanitize_like(query)
        base_filter = (
            FileRecord.organization_id == organization_id,
            func.lower(FileRecord.file_name).like(pattern),
        )

        count_stmt = select(func.count()).select_from(FileRecord).where(*base_filter)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(FileRecord)
            .where(*base_filter)
            .order_by(FileRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.db.execute(stmt)).scalars().all()

        results = [
            {
                "id": str(r.id),
                "file_name": r.file_name,
                "file_size": r.file_size,
                "uploaded_by": str(r.uploaded_by),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
        return results, total

    async def search_members(
        self, organization_id: UUID, query: str, limit: int, offset: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        pattern = self._sanitize_like(query)
        base_filter = (
            Membership.organization_id == organization_id,
            func.lower(User.email).like(pattern),
        )

        count_stmt = (
            select(func.count())
            .select_from(Membership)
            .join(User, Membership.user_id == User.id)
            .where(*base_filter)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Membership, User)
            .join(User, Membership.user_id == User.id)
            .where(*base_filter)
            .order_by(User.email.asc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.db.execute(stmt)).all()

        results = [
            {
                "id": str(m.id),
                "user_id": str(u.id),
                "email": u.email,
                "role": m.role.value if hasattr(m.role, "value") else str(m.role),
            }
            for m, u in rows
        ]
        return results, total

    async def search_audit_logs(
        self, organization_id: UUID, query: str, limit: int, offset: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        pattern = self._sanitize_like(query)
        base_filter = (
            AuditLog.organization_id == organization_id,
            or_(
                func.lower(AuditLog.action).like(pattern),
                func.lower(AuditLog.resource_type).like(pattern),
            ),
        )

        count_stmt = select(func.count()).select_from(AuditLog).where(*base_filter)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(AuditLog)
            .where(*base_filter)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.db.execute(stmt)).scalars().all()

        results = [
            {
                "id": str(a.id),
                "action": a.action.value if hasattr(a.action, "value") else str(a.action),
                "resource_type": a.resource_type,
                "resource_id": str(a.resource_id) if a.resource_id else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in rows
        ]
        return results, total
