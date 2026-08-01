import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from app.core.database import Base

class SearchIndexFailure(Base):
    __tablename__ = "search_index_failures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[str] = mapped_column(String(255), nullable=True)
    index_name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_id: Mapped[str] = mapped_column(String(255), nullable=False)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)  # "index" or "delete"
    error_message: Mapped[str] = mapped_column(String(1024), nullable=True)
    payload: Mapped[dict | None] = mapped_column(
        "payload",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
