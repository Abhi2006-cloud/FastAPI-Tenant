"""
MEMBERSHIPS MODULE — models.py

Membership = link between User and Organization (the multi-tenant join table).
Role controls what the user can do inside that tenant.

This table is the source of truth for "can user X access org Y?"
"""

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MembershipRole(str, enum.Enum):
    OWNER = "owner"   # full control; created org
    ADMIN = "admin"   # can invite users
    MEMBER = "member"  # normal access (files, etc.)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        # One row per user per organization
        UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[MembershipRole] = mapped_column(
        Enum(MembershipRole, name="membership_role", native_enum=False),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="memberships")  # noqa: F821
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        back_populates="memberships"
    )
