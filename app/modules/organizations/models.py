"""
ORGANIZATIONS MODULE — models.py

Organization = tenant / workspace. All tenant-owned data (files, invites) links here.
owner_id is the user who created the org; they also get a Membership row with role=owner.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    plan: Mapped[str] = mapped_column(String(32), default="free", nullable=False)
    plan_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    owner: Mapped["User"] = relationship(  # noqa: F821
        back_populates="owned_organizations",
        foreign_keys=[owner_id],
    )
    memberships: Mapped[list["Membership"]] = relationship(  # noqa: F821
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[list["Invitation"]] = relationship(  # noqa: F821
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    files: Mapped[list["FileRecord"]] = relationship(  # noqa: F821
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    upgrade_requests: Mapped[list["UpgradeRequest"]] = relationship(  # noqa: F821
        back_populates="organization",
        cascade="all, delete-orphan",
    )
