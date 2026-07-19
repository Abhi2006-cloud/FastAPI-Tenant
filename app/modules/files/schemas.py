"""FILES MODULE — schemas.py."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    uploaded_by: UUID
    file_name: str
    file_path: str
    file_size: int
    created_at: datetime


class FileDetailResponse(BaseModel):
    """Detailed file response with size and download URL."""
    
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    uploaded_by: UUID
    file_name: str
    file_path: str
    file_size: int
    created_at: datetime
    download_url: str


class FileStatisticsResponse(BaseModel):
    """File statistics for an organization."""
    
    total_files: int
    total_size_bytes: int
    average_file_size: int


class DeleteResponse(BaseModel):
    """Response after successful file deletion."""
    
    message: str = "file deleted"
