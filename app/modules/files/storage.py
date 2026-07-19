"""
FILES MODULE — storage.py

Storage abstraction layer for file operations.
Current implementation uses local disk storage.
Designed for easy migration to cloud storage (S3, R2, etc.) in the future.
"""

import logging
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)


class StorageService:
    """Storage abstraction for file operations."""
    
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
    
    def save(self, file_path: Path, content: bytes) -> None:
        """Save file content to storage."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
    
    def delete(self, file_path: Path) -> bool:
        """Delete file from storage. Returns True if deleted, False if not found."""
        try:
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to delete file {file_path}: {e}")
            return False
    
    def exists(self, file_path: Path) -> bool:
        """Check if file exists in storage."""
        return file_path.exists()
    
    def read(self, file_path: Path) -> bytes:
        """Read file content from storage."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return file_path.read_bytes()
    
    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return file_path.stat().st_size
