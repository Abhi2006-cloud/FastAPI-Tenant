"""
AUTH MODULE — session_model.py

Persistent user session backed by a refresh token.

One session = one logged-in device. Sessions are never deleted immediately;
they are revoked (revoked_at set) or cleaned up by a background job after
expiry.  Access tokens are short-lived JWTs and NOT stored here.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserSession(Base):
    """One row per active (or recently revoked) login session."""

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_expires_at", "expires_at"),
        Index("ix_user_sessions_user_revoked", "user_id", "revoked_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        # index=True omitted — covered by ix_user_sessions_user_revoked above
    )
    # SHA-256 hex digest of the raw refresh token — never store plaintext
    refresh_token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )

    # Device / client metadata (populated from User-Agent on login)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(128), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max 45 chars
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Soft-delete flag — True until revoked or expired
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ORM relationship back to User
    user: Mapped["User"] = relationship(back_populates="sessions")  # noqa: F821

    @property
    def is_active(self) -> bool:
        """True iff not revoked AND not past expiry."""
        if self.is_revoked:
            return False
        now = datetime.now(UTC)
        expires = self.expires_at
        # SQLite returns timezone-naive datetimes; normalize for comparison
        if expires.tzinfo is None:
            from datetime import timezone
            expires = expires.replace(tzinfo=timezone.utc)
        return expires > now
