"""phase2 plans, upgrade requests, and demo mode

Revision ID: 20260802_0008
Revises: 20260802_0007
Create Date: 2026-08-02 00:08:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260802_0008"
down_revision: Union[str, None] = "20260802_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    # 1. Add plan columns to organizations
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.add_column(
            sa.Column("plan", sa.String(length=32), nullable=False, server_default="free")
        )
        batch_op.add_column(
            sa.Column("plan_updated_at", sa.DateTime(timezone=True), nullable=True)
        )

    # 2. Create upgrade_requests table
    uuid_type = postgresql.UUID(as_uuid=True) if dialect_name == "postgresql" else sa.UUID()
    op.create_table(
        "upgrade_requests",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_by",
            uuid_type,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("requested_plan", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_upgrade_requests_organization_id"),
        "upgrade_requests",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_upgrade_requests_requested_by"),
        "upgrade_requests",
        ["requested_by"],
        unique=False,
    )

    # 3. Add demo columns to users
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("false" if dialect_name == "postgresql" else "0"))
        )
        batch_op.add_column(
            sa.Column("demo_expires_at", sa.DateTime(timezone=True), nullable=True)
        )

    # 4. Alter audit_logs.action and invitations.status column widths if on PostgreSQL
    if dialect_name == "postgresql":
        op.alter_column(
            "audit_logs",
            "action",
            type_=sa.String(length=64),
            existing_type=sa.String(length=21),
            existing_nullable=False,
        )
        op.alter_column(
            "invitations",
            "status",
            type_=sa.String(length=32),
            existing_type=sa.String(length=8),
            existing_nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.alter_column(
            "invitations",
            "status",
            type_=sa.String(length=8),
            existing_type=sa.String(length=32),
            existing_nullable=False,
        )
        op.alter_column(
            "audit_logs",
            "action",
            type_=sa.String(length=21),
            existing_type=sa.String(length=64),
            existing_nullable=False,
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("demo_expires_at")
        batch_op.drop_column("is_demo")

    op.drop_index(op.f("ix_upgrade_requests_requested_by"), table_name="upgrade_requests")
    op.drop_index(op.f("ix_upgrade_requests_organization_id"), table_name="upgrade_requests")
    op.drop_table("upgrade_requests")

    with op.batch_alter_table("organizations") as batch_op:
        batch_op.drop_column("plan_updated_at")
        batch_op.drop_column("plan")

