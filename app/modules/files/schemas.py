import mimetypes
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    uploaded_by: UUID
    file_name: str
    file_path: str
    file_size: int
    created_at: datetime

    @computed_field
    @property
    def filename(self) -> str:
        return self.file_name

    @computed_field
    @property
    def size_bytes(self) -> int:
        return self.file_size

    @computed_field
    @property
    def content_type(self) -> str:
        return mimetypes.guess_type(self.file_name)[0] or "application/octet-stream"


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

    @computed_field
    @property
    def filename(self) -> str:
        return self.file_name

    @computed_field
    @property
    def size_bytes(self) -> int:
        return self.file_size

    @computed_field
    @property
    def content_type(self) -> str:
        return mimetypes.guess_type(self.file_name)[0] or "application/octet-stream"


class FileStatisticsResponse(BaseModel):
    """File statistics for an organization."""
    
    total_files: int
    total_size_bytes: int
    average_file_size: int

    @computed_field
    @property
    def total_bytes(self) -> int:
        return self.total_size_bytes


class DeleteResponse(BaseModel):
    """Response after successful file deletion."""
    
    message: str = "file deleted"

