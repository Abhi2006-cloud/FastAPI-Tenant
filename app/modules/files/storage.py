"""
FILES MODULE — storage.py

Storage abstraction layer for file operations.
Supports local disk storage, S3-compatible cloud storage, and PostgreSQL BYTEA blob storage.
"""

import logging
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class StorageService:
    """Storage abstraction for file operations with local, S3, and postgres backends."""
    
    def __init__(self, base_path: Path, db: Optional[AsyncSession] = None) -> None:
        base_path.mkdir(parents=True, exist_ok=True)
        self.base_path = base_path.resolve()
        self.db = db
        self.settings = get_settings()
        self._s3_client = None
        
        if self.is_s3_enabled():
            try:
                import boto3
                kwargs = {
                    "aws_access_key_id": self.settings.s3_access_key_id,
                    "aws_secret_access_key": self.settings.s3_secret_access_key,
                    "region_name": self.settings.s3_region or "auto",
                }
                if self.settings.s3_endpoint_url:
                    kwargs["endpoint_url"] = self.settings.s3_endpoint_url
                self._s3_client = boto3.client("s3", **kwargs)
                logger.info("S3 Cloud Storage backend initialized for bucket '%s'", self.settings.s3_bucket_name)
            except Exception as e:
                logger.warning("Failed to initialize S3 client: %s. Falling back to local storage.", e)
                self._s3_client = None

    @property
    def backend(self) -> str:
        """Select storage backend: 'postgres' | 's3' | 'local'."""
        configured = (getattr(self.settings, "storage_backend", None) or "local").lower()
        if configured in ("postgres", "postgresql", "pg"):
            return "postgres"
        if configured == "s3" or self.is_s3_enabled():
            return "s3"
        return "local"

    @staticmethod
    def is_pg_path(file_path: Path | str) -> bool:
        """Check if path is a PostgreSQL pseudo-path ('pg://<org_id>/<file_id>')."""
        return str(file_path).startswith("pg://")

    @staticmethod
    def parse_pg_path(file_path: Path | str) -> tuple[str, UUID]:
        """Extract organization_id and file_id from a postgres pseudo-path."""
        raw = str(file_path)
        if not raw.startswith("pg://"):
            raise ValueError(f"Invalid postgres storage path: {raw}")
        parts = raw[5:].split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid postgres storage path format: {raw}")
        return parts[0], UUID(parts[1])

    async def save_blob(self, file_id: UUID, content: bytes) -> None:
        """Persist binary blob directly into the PostgreSQL file_blobs table."""
        if self.db is None:
            raise RuntimeError("Database session required for postgres storage backend")
        from app.modules.files.blob_model import FileBlob
        blob = FileBlob(file_id=file_id, content=content)
        self.db.add(blob)
        await self.db.flush()

    async def read_blob(self, file_id: UUID) -> bytes:
        """Retrieve binary blob from PostgreSQL file_blobs table."""
        if self.db is None:
            raise RuntimeError("Database session required for postgres storage backend")
        from app.modules.files.blob_model import FileBlob
        from sqlalchemy import select
        result = await self.db.execute(select(FileBlob.content).where(FileBlob.file_id == file_id))
        content = result.scalar_one_or_none()
        if content is None:
            raise FileNotFoundError(f"Blob not found for file_id: {file_id}")
        return content

    async def delete_blob(self, file_id: UUID) -> bool:
        """Delete binary blob from PostgreSQL file_blobs table."""
        if self.db is None:
            raise RuntimeError("Database session required for postgres storage backend")
        from app.modules.files.blob_model import FileBlob
        from sqlalchemy import delete
        result = await self.db.execute(delete(FileBlob).where(FileBlob.file_id == file_id))
        return bool(result.rowcount and result.rowcount > 0)

    async def exists_blob(self, file_id: UUID) -> bool:
        """Check if binary blob exists in PostgreSQL file_blobs table."""
        if self.db is None:
            raise RuntimeError("Database session required for postgres storage backend")
        from app.modules.files.blob_model import FileBlob
        from sqlalchemy import select, func
        result = await self.db.execute(
            select(func.count()).select_from(FileBlob).where(FileBlob.file_id == file_id)
        )
        count = result.scalar() or 0
        return count > 0

    async def get_blob_size(self, file_id: UUID) -> int:
        """Get binary blob size in bytes from PostgreSQL file_blobs table."""
        if self.db is None:
            raise RuntimeError("Database session required for postgres storage backend")
        from app.modules.files.blob_model import FileBlob
        from sqlalchemy import select, func
        result = await self.db.execute(
            select(func.length(FileBlob.content)).where(FileBlob.file_id == file_id)
        )
        size = result.scalar_one_or_none()
        if size is None:
            raise FileNotFoundError(f"Blob not found for file_id: {file_id}")
        return size

    async def async_save(
        self,
        file_path: Path | str,
        content: bytes,
        file_id: Optional[UUID] = None,
    ) -> str:
        """Unified async save supporting postgres, S3, and local storage."""
        if self.backend == "postgres" or self.is_pg_path(file_path):
            fid = file_id
            if fid is None and self.is_pg_path(file_path):
                _, fid = self.parse_pg_path(file_path)
            if fid is None:
                raise ValueError("file_id required for postgres storage backend")
            await self.save_blob(fid, content)
            return str(file_path)

        p = Path(file_path) if isinstance(file_path, str) else file_path
        self.save(p, content)
        return str(file_path)

    async def async_read(self, file_path: Path | str) -> bytes:
        """Unified async read supporting postgres, S3, and local storage."""
        if self.is_pg_path(file_path):
            _, fid = self.parse_pg_path(file_path)
            return await self.read_blob(fid)
        p = Path(file_path) if isinstance(file_path, str) else file_path
        return self.read(p)

    async def async_delete(self, file_path: Path | str) -> bool:
        """Unified async delete supporting postgres, S3, and local storage."""
        if self.is_pg_path(file_path):
            _, fid = self.parse_pg_path(file_path)
            return await self.delete_blob(fid)
        p = Path(file_path) if isinstance(file_path, str) else file_path
        return self.delete(p)

    async def async_exists(self, file_path: Path | str) -> bool:
        """Unified async exists check supporting postgres, S3, and local storage."""
        if self.is_pg_path(file_path):
            _, fid = self.parse_pg_path(file_path)
            return await self.exists_blob(fid)
        p = Path(file_path) if isinstance(file_path, str) else file_path
        return self.exists(p)

    def _validate_path(self, file_path: Path) -> Path:
        """
        Validate and resolve a file path to prevent directory traversal and symlink escapes.
        
        Ensures the canonical resolved path remains strictly within self.base_path.
        Raises ForbiddenError if traversal is detected.
        """
        from app.core.exceptions import ForbiddenError

        base = self.base_path.resolve()
        if not file_path.is_absolute():
            resolved = (base / file_path).resolve()
        else:
            resolved = file_path.resolve()

        try:
            is_contained = resolved.is_relative_to(base)
        except AttributeError:
            is_contained = str(resolved).startswith(str(base))

        if not is_contained:
            logger.warning("Path traversal attempt detected: path=%s resolved=%s base=%s", file_path, resolved, base)
            raise ForbiddenError("Path traversal detected: Access denied outside storage root")

        return resolved

    def is_s3_enabled(self) -> bool:
        """Check if S3 configuration is present."""
        return bool(
            self.settings.s3_bucket_name
            and self.settings.s3_access_key_id
            and self.settings.s3_secret_access_key
        )
    
    def _s3_key(self, file_path: Path) -> str:
        """Convert path relative to base_path into an S3 object key."""
        safe_path = self._validate_path(file_path)
        try:
            return str(safe_path.relative_to(self.base_path))
        except ValueError:
            return safe_path.name

    def save(self, file_path: Path, content: bytes) -> None:
        """Save file content to storage (S3 or local disk)."""
        safe_path = self._validate_path(file_path)
        if self._s3_client and self.settings.s3_bucket_name:
            key = self._s3_key(safe_path)
            self._s3_client.put_object(
                Bucket=self.settings.s3_bucket_name,
                Key=key,
                Body=content,
            )
            # Also mirror locally if desired or required
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_bytes(content)
            return

        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_bytes(content)
    
    def delete(self, file_path: Path) -> bool:
        """Delete file from storage. Returns True if deleted, False if not found."""
        safe_path = self._validate_path(file_path)
        deleted = False
        if self._s3_client and self.settings.s3_bucket_name:
            key = self._s3_key(safe_path)
            try:
                self._s3_client.delete_object(
                    Bucket=self.settings.s3_bucket_name,
                    Key=key,
                )
                deleted = True
            except Exception as e:
                logger.warning("Failed to delete S3 key %s: %s", key, e)

        try:
            if safe_path.exists():
                safe_path.unlink()
                deleted = True
        except Exception as e:
            logger.warning("Failed to delete local file %s: %s", safe_path, e)

        return deleted
    
    def exists(self, file_path: Path) -> bool:
        """Check if file exists in storage."""
        safe_path = self._validate_path(file_path)
        if self._s3_client and self.settings.s3_bucket_name:
            key = self._s3_key(safe_path)
            try:
                self._s3_client.head_object(
                    Bucket=self.settings.s3_bucket_name,
                    Key=key,
                )
                return True
            except Exception:
                pass
        return safe_path.exists()
    
    def read(self, file_path: Path) -> bytes:
        """Read file content from storage."""
        safe_path = self._validate_path(file_path)
        if self._s3_client and self.settings.s3_bucket_name:
            key = self._s3_key(safe_path)
            try:
                obj = self._s3_client.get_object(
                    Bucket=self.settings.s3_bucket_name,
                    Key=key,
                )
                return obj["Body"].read()
            except Exception as e:
                logger.warning("Failed to read S3 key %s: %s. Trying local fallback.", key, e)

        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {safe_path}")
        return safe_path.read_bytes()
    
    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes."""
        safe_path = self._validate_path(file_path)
        if self._s3_client and self.settings.s3_bucket_name:
            key = self._s3_key(safe_path)
            try:
                obj = self._s3_client.head_object(
                    Bucket=self.settings.s3_bucket_name,
                    Key=key,
                )
                return obj["ContentLength"]
            except Exception:
                pass

        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {safe_path}")
        return safe_path.stat().st_size

