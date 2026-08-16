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
        self.base_path = base_path
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

    def is_s3_enabled(self) -> bool:
        """Check if S3 configuration is present."""
        return bool(
            self.settings.s3_bucket_name
            and self.settings.s3_access_key_id
            and self.settings.s3_secret_access_key
        )
    
    def _s3_key(self, file_path: Path) -> str:
        """Convert path relative to base_path into an S3 object key."""
        try:
            return str(file_path.relative_to(self.base_path))
        except ValueError:
            return file_path.name

    def save(self, file_path: Path, content: bytes) -> None:
        """Save file content to storage (S3 or local disk)."""
        if self._s3_client and self.settings.s3_bucket_name:
            key = self._s3_key(file_path)
            self._s3_client.put_object(
                Bucket=self.settings.s3_bucket_name,
                Key=key,
                Body=content,
            )
            # Also mirror locally if desired or required
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)
            return

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
    
    def delete(self, file_path: Path) -> bool:
        """Delete file from storage. Returns True if deleted, False if not found."""
        deleted = False
        if self._s3_client and self.settings.s3_bucket_name:
            key = self._s3_key(file_path)
            try:
                self._s3_client.delete_object(
                    Bucket=self.settings.s3_bucket_name,
                    Key=key,
                )
                deleted = True
            except Exception as e:
                logger.warning("Failed to delete S3 key %s: %s", key, e)

        try:
            if file_path.exists():
                file_path.unlink()
                deleted = True
        except Exception as e:
            logger.warning("Failed to delete local file %s: %s", file_path, e)

        return deleted
    
    def exists(self, file_path: Path) -> bool:
        """Check if file exists in storage."""
        if self._s3_client and self.settings.s3_bucket_name:
            key = self._s3_key(file_path)
            try:
                self._s3_client.head_object(
                    Bucket=self.settings.s3_bucket_name,
                    Key=key,
                )
                return True
            except Exception:
                pass
        return file_path.exists()
    
    def read(self, file_path: Path) -> bytes:
        """Read file content from storage."""
        if self._s3_client and self.settings.s3_bucket_name:
            key = self._s3_key(file_path)
            try:
                obj = self._s3_client.get_object(
                    Bucket=self.settings.s3_bucket_name,
                    Key=key,
                )
                return obj["Body"].read()
            except Exception as e:
                logger.warning("Failed to read S3 key %s: %s. Trying local fallback.", key, e)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return file_path.read_bytes()
    
    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes."""
        if self._s3_client and self.settings.s3_bucket_name:
            key = self._s3_key(file_path)
            try:
                obj = self._s3_client.head_object(
                    Bucket=self.settings.s3_bucket_name,
                    Key=key,
                )
                return obj["ContentLength"]
            except Exception:
                pass

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return file_path.stat().st_size

