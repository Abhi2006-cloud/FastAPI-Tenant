"""
FILES MODULE — repository.py

Always filter by organization_id so one tenant cannot list another's files.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.files.models import FileRecord


class FileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, file_record: FileRecord) -> FileRecord:
        self.db.add(file_record)
        await self.db.flush()
        await self.db.refresh(file_record)
        return file_record

    async def list_by_organization(self, organization_id: UUID) -> list[FileRecord]:
        result = await self.db.execute(
            select(FileRecord)
            .where(FileRecord.organization_id == organization_id)
            .order_by(FileRecord.created_at.desc())
        )
        return list(result.scalars().all())
