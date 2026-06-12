"""
File upload helpers (not tied to HTTP).

Used by files/service.py to validate uploads and build per-tenant paths on disk.
"""

import re
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import BadRequestError

settings = get_settings()

SAFE_FILENAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]")
ALLOWED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".csv",
    ".json",
    ".md",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}


def sanitize_filename(filename: str) -> str:
    """Strip path traversal and unsafe characters from client-provided names."""
    name = Path(filename).name
    sanitized = SAFE_FILENAME_PATTERN.sub("_", name).strip("._")
    if not sanitized:
        raise BadRequestError("Invalid file name")
    return sanitized[:255]


def validate_upload(file: UploadFile) -> str:
    if not file.filename:
        raise BadRequestError("File name is required")

    safe_name = sanitize_filename(file.filename)
    extension = Path(safe_name).suffix.lower()
    if extension and extension not in ALLOWED_EXTENSIONS:
        raise BadRequestError(f"File type '{extension}' is not allowed")

    return safe_name


def organization_upload_dir(organization_id: UUID) -> Path:
    """One folder per tenant — physical isolation on disk."""
    path = Path(settings.upload_dir) / str(organization_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_storage_path(organization_id: UUID, file_name: str) -> Path:
    """Unique filename avoids collisions when two users upload report.pdf."""
    unique_name = f"{uuid4()}_{file_name}"
    return organization_upload_dir(organization_id) / unique_name
