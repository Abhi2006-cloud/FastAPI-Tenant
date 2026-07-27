"""AUDIT MODULE — schemas.py (API request/response shapes)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.audit.events import AuditAction


class AuditLogResponse(BaseModel):
    """Single audit log entry returned to clients."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    organization_id: UUID
    actor_user_id: UUID | None
    action: AuditAction
    resource_type: str
    resource_id: UUID | None
    metadata: dict | None = Field(default=None, validation_alias="metadata_")
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Paginated list of audit log entries."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


class AuditLogSearchResponse(BaseModel):
    """Paginated search results for audit log entries."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    query: str | None = None
