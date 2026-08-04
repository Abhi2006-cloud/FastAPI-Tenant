"""
AUTH MODULE — models.py

User is global (not tied to one organization). Users join tenants via Membership.
Passwords are stored as bcrypt hashes only.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Orgs this user belongs to (via memberships table)
    memberships: Mapped[list["Membership"]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
    )
    # Orgs this user created as owner_id on Organization
    owned_organizations: Mapped[list["Organization"]] = relationship(  # noqa: F821
        back_populates="owner",
        foreign_keys="Organization.owner_id",
    )
    uploaded_files: Mapped[list["FileRecord"]] = relationship(  # noqa: F821
        back_populates="uploaded_by_user",
    )
    # Active login sessions (via user_sessions table)
    sessions: Mapped[list["UserSession"]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
    )
