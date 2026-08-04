"""
AUTH MODULE — auth_audit_model.py

User-scoped authentication audit log.

Unlike the org-scoped AuditLog (audit_logs table), auth events are global —
they occur before/after an org context is known. This separate table avoids
requiring organization_id on authentication events.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


class AuthEventType(str, enum.Enum):
    """Enumeration of all authentication events logged to auth_audit_logs."""

    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGOUT_ALL = "LOGOUT_ALL"
    REFRESH = "REFRESH"
    REPLAY_ATTACK = "REPLAY_ATTACK"
    SESSION_REVOKED = "SESSION_REVOKED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    NEW_DEVICE_LOGIN = "NEW_DEVICE_LOGIN"


class AuthAuditLog(Base):
    """Append-only log of authentication events for a user (not org-scoped)."""

    __tablename__ = "auth_audit_logs"
    # Named composite indexes only — column-level index=True is omitted to
    # avoid duplicate index errors when SQLAlchemy and __table_args__ both
    # attempt to create the same index (especially visible in SQLite tests).
    __table_args__ = (
        Index("ix_auth_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_auth_audit_logs_event_type", "event_type"),
        Index("ix_auth_audit_logs_user_id", "user_id"),
        Index("ix_auth_audit_logs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        # index=True omitted — covered by ix_auth_audit_logs_user_id above
    )
    event_type: Mapped[AuthEventType] = mapped_column(
        Enum(AuthEventType, name="auth_event_type", native_enum=False),
        nullable=False,
        # index=True omitted — covered by ix_auth_audit_logs_event_type above
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # JSONB on PostgreSQL; JSON fallback for SQLite tests
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        # index=True omitted — covered by ix_auth_audit_logs_created_at above
    )
