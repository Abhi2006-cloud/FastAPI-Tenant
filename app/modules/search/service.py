"""
SEARCH MODULE — service.py

Business logic service for tenant-scoped basic search queries over Postgres / SQLite.
Layering: router -> service -> repository.
"""

from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.search.repository import BasicSearchRepository


class BasicSearchService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = BasicSearchRepository(db)

    async def search_basic(
        self, organization_id: UUID, query: str, limit: int = 10, offset: int = 0
    ) -> Dict[str, Any]:
        files, total_files = await self.repo.search_files(
            organization_id=organization_id, query=query, limit=limit, offset=offset
        )
        members, total_members = await self.repo.search_members(
            organization_id=organization_id, query=query, limit=limit, offset=offset
        )
        audit_logs, total_audit_logs = await self.repo.search_audit_logs(
            organization_id=organization_id, query=query, limit=limit, offset=offset
        )

        return {
            "query": query,
            "organization_id": str(organization_id),
            "files": files,
            "members": members,
            "audit_logs": audit_logs,
            "totals": {
                "files": total_files,
                "members": total_members,
                "audit_logs": total_audit_logs,
                "total": total_files + total_members + total_audit_logs,
            },
        }
