"""
FILES MODULE — storage.py

Storage abstraction layer for file operations.
Supports local disk storage and S3-compatible cloud storage (Cloudflare R2, AWS S3, etc.).
"""

import logging
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class StorageService:
    """Storage abstraction for file operations with optional S3 cloud backend."""
    
    def __init__(self, base_path: Path) -> None:
        base_path.mkdir(parents=True, exist_ok=True)
        self.base_path = base_path.resolve()
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

