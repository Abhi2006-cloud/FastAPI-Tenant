"""EMAIL MODULE — schemas.py"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.modules.email.models import EmailStatus


class EmailLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: Optional[UUID] = None
    recipient_email: str
    provider: str
    template_name: str
    subject: str
    status: EmailStatus
    provider_message_id: Optional[str] = None
    rq_job_id: Optional[str] = None
    retry_count: int
    sent_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = None
    created_at: datetime


class SendTestEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str = "Test Email from AI Workspace"
    template_name: str = "welcome.html"
    context: Optional[Dict[str, Any]] = None


class EmailLogListResponse(BaseModel):
    logs: List[EmailLogResponse]
    total: int


class EmailStatsResponse(BaseModel):
    total_emails: int
    status_counts: Dict[str, int]
    success_rate_percent: float
    active_provider: str
    health_status: Dict[str, Any]
