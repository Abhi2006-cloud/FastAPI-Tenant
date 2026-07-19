"""
FILES MODULE — repository.py

Always filter by organization_id so one tenant cannot list another's files.
"""

from uuid import UUID

from sqlalchemy import func, select
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

    async def get_by_id(self, file_id: UUID) -> FileRecord | None:
        result = await self.db.execute(
            select(FileRecord).where(FileRecord.id == file_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, file_id: UUID) -> bool:
        """Delete a file record. Returns True if deleted, False if not found."""
        file_record = await self.get_by_id(file_id)
        if file_record is None:
            return False
        await self.db.delete(file_record)
        await self.db.flush()
        return True

    async def get_statistics(self, organization_id: UUID) -> dict:
        """Get file statistics for an organization."""
        result = await self.db.execute(
            select(
                func.count(FileRecord.id).label("total_files"),
                func.sum(FileRecord.file_size).label("total_size_bytes"),
            )
            .where(FileRecord.organization_id == organization_id)
        )
        row = result.one_or_none()
        if row is None or row.total_files == 0:
            return {"total_files": 0, "total_size_bytes": 0, "average_file_size": 0}
        
        total_files = row.total_files or 0
        total_size = row.total_size_bytes or 0
        average_size = total_size // total_files if total_files > 0 else 0
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "average_file_size": average_size,
        }
