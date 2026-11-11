"""
FILES MODULE — service.py

Every operation calls ensure_member first (defense in depth with router Depends).
Disk layout: uploads/<org_id>/<uuid>_<filename>
"""

from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.jobs.tasks import process_file_upload_task, index_file_task, delete_file_task
from app.modules.audit.events import RESOURCE_FILE, AuditAction
from app.modules.audit.service import AuditLogService
from app.modules.billing.plans import get_plan_limits
from app.modules.files.models import FileRecord
from app.modules.files.repository import FileRepository
from app.modules.files.storage import StorageService
from app.modules.memberships.models import MembershipRole
from app.modules.memberships.service import MembershipService
from app.modules.organizations.repository import OrganizationRepository
from app.services.job_service import JobService
from app.utils.files import build_storage_path, validate_upload

settings = get_settings()


class FileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = FileRepository(db)
        self.membership_service = MembershipService(db)
        self.storage = StorageService(Path(settings.upload_dir), db=db)
        self.job_service = JobService()

    async def upload_file(
        self,
        user_id: UUID,
        organization_id: UUID,
        upload: UploadFile,
    ) -> FileRecord:
        await self.membership_service.ensure_member(user_id, organization_id)

        # ── Plan limits enforcement: max_files & org_storage_mb ──────────────
        org = await OrganizationRepository(self.db).get_by_id(organization_id)
        plan_str = org.plan if org else "free"
        limits = get_plan_limits(plan_str)

        stats = await self.repo.get_statistics(organization_id)
        current_files = stats["total_files"]
        current_storage_bytes = stats["total_size_bytes"]

        if current_files >= limits.max_files:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "PLAN_LIMIT_REACHED",
                    "limit": "max_files",
                    "current": current_files,
                    "max": limits.max_files,
                    "plan": plan_str,
                },
            )

        safe_name = validate_upload(upload)
        chunk_size = 64 * 1024
        total_size = 0
        current_settings = get_settings()
        max_bytes = limits.max_upload_bytes

        if self.storage.backend == "postgres":
            chunks: list[bytes] = []
            while True:
                chunk = await upload.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
                if current_settings.max_upload_size_bytes < limits.max_upload_bytes and total_size > current_settings.max_upload_size_bytes:
                    raise BadRequestError(f"File exceeds maximum size of {current_settings.max_upload_size_mb} MB")
                if total_size > max_bytes:
                    raise HTTPException(
                        status_code=402,
                        detail={
                            "code": "PLAN_LIMIT_REACHED",
                            "limit": "max_upload_mb",
                            "current": round(total_size / (1024 * 1024), 2),
                            "max": limits.max_upload_mb,
                            "plan": plan_str,
                        },
                    )
                chunks.append(chunk)

            if total_size == 0:
                raise BadRequestError("Empty file")

            if current_storage_bytes + total_size > limits.org_storage_bytes:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "code": "PLAN_LIMIT_REACHED",
                        "limit": "org_storage_mb",
                        "current": round((current_storage_bytes + total_size) / (1024 * 1024), 2),
                        "max": limits.org_storage_mb,
                        "plan": plan_str,
                    },
                )

            import uuid
            file_id = uuid.uuid4()
            storage_path = f"pg://{organization_id}/{file_id}"
            file_content = b"".join(chunks)

            record = FileRecord(
                id=file_id,
                organization_id=organization_id,
                uploaded_by=user_id,
                file_name=safe_name,
                file_path=storage_path,
                file_size=total_size,
            )
            created = await self.repo.create(record)
            await self.storage.save_blob(file_id, file_content)
            await self.db.commit()
        else:
            storage_path_obj = build_storage_path(organization_id, safe_name)
            safe_storage_path = self.storage._validate_path(storage_path_obj)
            safe_storage_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                with open(safe_storage_path, "wb") as f:
                    while True:
                        chunk = await upload.read(chunk_size)
                        if not chunk:
                            break
                        total_size += len(chunk)
                        if current_settings.max_upload_size_bytes < limits.max_upload_bytes and total_size > current_settings.max_upload_size_bytes:
                            if safe_storage_path.exists():
                                safe_storage_path.unlink()
                            raise BadRequestError(f"File exceeds maximum size of {current_settings.max_upload_size_mb} MB")
                        if total_size > max_bytes:
                            raise HTTPException(
                                status_code=402,
                                detail={
                                    "code": "PLAN_LIMIT_REACHED",
                                    "limit": "max_upload_mb",
                                    "current": round(total_size / (1024 * 1024), 2),
                                    "max": limits.max_upload_mb,
                                    "plan": plan_str,
                                },
                            )
                        f.write(chunk)

                if total_size == 0:
                    if safe_storage_path.exists():
                        safe_storage_path.unlink()
                    raise BadRequestError("Empty file")

                if current_storage_bytes + total_size > limits.org_storage_bytes:
                    if safe_storage_path.exists():
                        safe_storage_path.unlink()
                    raise HTTPException(
                        status_code=402,
                        detail={
                            "code": "PLAN_LIMIT_REACHED",
                            "limit": "org_storage_mb",
                            "current": round((current_storage_bytes + total_size) / (1024 * 1024), 2),
                            "max": limits.org_storage_mb,
                            "plan": plan_str,
                        },
                    )

                # Mirror to S3 if enabled
                if self.storage._s3_client and self.storage.settings.s3_bucket_name:
                    key = self.storage._s3_key(safe_storage_path)
                    with open(safe_storage_path, "rb") as f:
                        self.storage._s3_client.put_object(
                            Bucket=self.storage.settings.s3_bucket_name,
                            Key=key,
                            Body=f.read(),
                        )
            except Exception:
                # Clean up partially written file on any error
                if safe_storage_path.exists():
                    try:
                        safe_storage_path.unlink()
                    except Exception:
                        pass
                raise

            try:
                record = FileRecord(
                    organization_id=organization_id,
                    uploaded_by=user_id,
                    file_name=safe_name,
                    file_path=str(safe_storage_path),
                    file_size=total_size,
                )
                created = await self.repo.create(record)
                await self.db.commit()
            except Exception:
                # Clean up storage file if database persist fails to avoid orphaned files
                self.storage.delete(safe_storage_path)
                raise

        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=user_id,
            action=AuditAction.FILE_UPLOADED,
            resource_type=RESOURCE_FILE,
            resource_id=created.id,
            metadata={"file_name": safe_name, "file_size": total_size},
        )
        await self.db.commit()

        # Worker post-processing (metadata collection; future: virus scan, thumbnails).
        # In JOB_SYNC_MODE the request session is the source of truth; skip separate DB work.
        if not settings.job_sync_mode:
            self.job_service.enqueue(
                process_file_upload_task,
                str(created.id),
                str(organization_id),
                organization_id=organization_id,
            )
        
        # Enqueue search indexing task only if search enabled
        if settings.is_search_enabled:
            self.job_service.enqueue(index_file_task, str(created.id), organization_id=organization_id)
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

        if not await self.storage.async_exists(file_record.file_path):
            raise NotFoundError("File not found on storage")

        content = await self.storage.async_read(file_record.file_path)
        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=user_id,
            action=AuditAction.FILE_DOWNLOADED,
            resource_type=RESOURCE_FILE,
            resource_id=file_id,
            metadata={"file_name": file_record.file_name, "file_size": file_record.file_size},
        )
        await self.db.commit()
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
        
        # Delete storage blob/file first or delete database record
        await self.storage.async_delete(file_record.file_path)
        await self.repo.delete(file_id)
        await self.db.commit()

        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=user_id,
            action=AuditAction.FILE_DELETED,
            resource_type=RESOURCE_FILE,
            resource_id=file_id,
            metadata=file_metadata,
        )
        await self.db.commit()
        
        # Enqueue search deletion task only if search enabled
        if settings.is_search_enabled:
            self.job_service.enqueue(delete_file_task, str(file_id), str(organization_id), organization_id=organization_id)

    async def get_statistics(
        self, user_id: UUID, organization_id: UUID
    ) -> dict:
        """Get file statistics for the organization."""
        await self.membership_service.ensure_member(user_id, organization_id)
        return await self.repo.get_statistics(organization_id)
