"""
FILES MODULE — service.py

Every operation calls ensure_member first (defense in depth with router Depends).
Disk layout: uploads/<org_id>/<uuid>_<filename>
"""

from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.modules.files.models import FileRecord
from app.modules.files.repository import FileRepository
from app.modules.memberships.service import MembershipService
from app.utils.files import build_storage_path, validate_upload

settings = get_settings()


class FileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = FileRepository(db)
        self.membership_service = MembershipService(db)

    async def upload_file(
        self,
        user_id: UUID,
        organization_id: UUID,
        upload: UploadFile,
    ) -> FileRecord:
        await self.membership_service.ensure_member(user_id, organization_id)

        safe_name = validate_upload(upload)
        content = await upload.read()
        if not content:
            raise BadRequestError("Empty file")

        if len(content) > settings.max_upload_size_bytes:
            raise BadRequestError(
                f"File exceeds maximum size of {settings.max_upload_size_mb} MB"
            )

        storage_path = build_storage_path(organization_id, safe_name)
        storage_path.write_bytes(content)

        record = FileRecord(
            organization_id=organization_id,
            uploaded_by=user_id,
            file_name=safe_name,
            file_path=str(storage_path),
        )
        return await self.repo.create(record)

    async def list_files(self, user_id: UUID, organization_id: UUID) -> list[FileRecord]:
        await self.membership_service.ensure_member(user_id, organization_id)
        return await self.repo.list_by_organization(organization_id)
