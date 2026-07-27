"""
FILES MODULE — service.py

Every operation calls ensure_member first (defense in depth with router Depends).
Disk layout: uploads/<org_id>/<uuid>_<filename>
"""

from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.modules.audit.events import RESOURCE_FILE, AuditAction
from app.modules.audit.service import AuditLogService
from app.modules.files.models import FileRecord
from app.modules.files.repository import FileRepository
from app.modules.files.storage import StorageService
from app.modules.memberships.models import MembershipRole
from app.modules.memberships.service import MembershipService
from app.utils.files import build_storage_path, validate_upload

settings = get_settings()


class FileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = FileRepository(db)
        self.membership_service = MembershipService(db)
        self.storage = StorageService(Path(settings.upload_dir))

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
        self.storage.save(storage_path, content)

        record = FileRecord(
            organization_id=organization_id,
            uploaded_by=user_id,
            file_name=safe_name,
            file_path=str(storage_path),
            file_size=len(content),
        )
        created = await self.repo.create(record)
        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=user_id,
            action=AuditAction.FILE_UPLOADED,
            resource_type=RESOURCE_FILE,
            resource_id=created.id,
            metadata={"file_name": safe_name, "file_size": len(content)},
        )
        return created

    async def list_files(self, user_id: UUID, organization_id: UUID) -> list[FileRecord]:
        await self.membership_service.ensure_member(user_id, organization_id)
        return await self.repo.list_by_organization(organization_id)

    async def get_file(
        self, user_id: UUID, organization_id: UUID, file_id: UUID
    ) -> FileRecord:
        """Get file details with organization membership verification."""
        await self.membership_service.ensure_member(user_id, organization_id)
        
        file_record = await self.repo.get_by_id(file_id)
        if file_record is None:
            raise NotFoundError("File not found")
        
        if file_record.organization_id != organization_id:
            raise ForbiddenError("File does not belong to this organization")
        
        return file_record

    async def download_file(
        self, user_id: UUID, organization_id: UUID, file_id: UUID
    ) -> tuple[bytes, str]:
        """Download file content with organization membership verification."""
        file_record = await self.get_file(user_id, organization_id, file_id)

        file_path = Path(file_record.file_path)
        if not self.storage.exists(file_path):
            raise NotFoundError("File not found on storage")

        content = self.storage.read(file_path)
        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=user_id,
            action=AuditAction.FILE_DOWNLOADED,
            resource_type=RESOURCE_FILE,
            resource_id=file_id,
            metadata={"file_name": file_record.file_name, "file_size": file_record.file_size},
        )
        return content, file_record.file_name

    async def delete_file(
        self, user_id: UUID, organization_id: UUID, file_id: UUID
    ) -> None:
        """Delete file with RBAC enforcement."""
        membership = await self.membership_service.ensure_member(user_id, organization_id)
        
        file_record = await self.repo.get_by_id(file_id)
        if file_record is None:
            raise NotFoundError("File not found")
        
        if file_record.organization_id != organization_id:
            raise ForbiddenError("File does not belong to this organization")

        file_metadata = {
            "file_name": file_record.file_name,
            "file_size": file_record.file_size,
        }

        # RBAC: Owner and Admin can delete any file
        # Member can only delete files they uploaded
        if membership.role == MembershipRole.MEMBER:
            if file_record.uploaded_by != user_id:
                raise ForbiddenError("You can only delete files you uploaded")
        
        # Delete physical file
        file_path = Path(file_record.file_path)
        deleted = self.storage.delete(file_path)
        if not deleted:
            # Log warning but continue with metadata deletion
            pass
        
        # Delete database record
        await self.repo.delete(file_id)
        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=user_id,
            action=AuditAction.FILE_DELETED,
            resource_type=RESOURCE_FILE,
            resource_id=file_id,
            metadata=file_metadata,
        )

    async def get_statistics(
        self, user_id: UUID, organization_id: UUID
    ) -> dict:
        """Get file statistics for the organization."""
        await self.membership_service.ensure_member(user_id, organization_id)
        return await self.repo.get_statistics(organization_id)
