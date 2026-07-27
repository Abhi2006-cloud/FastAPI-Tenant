"""add audit_logs table

Revision ID: 20260721_0003
Revises: 20260719_0002
Create Date: 2026-07-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260721_0003"
down_revision: Union[str, None] = "20260719_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "action",
            sa.Enum(
                "ORGANIZATION_CREATED",
                "MEMBER_INVITED",
                "INVITATION_ACCEPTED",
                "MEMBER_ROLE_CHANGED",
                "MEMBER_REMOVED",
                "OWNERSHIP_TRANSFERRED",
                "FILE_UPLOADED",
                "FILE_DOWNLOADED",
                "FILE_DELETED",
                name="audit_action",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(
        op.f("ix_audit_logs_actor_user_id"), "audit_logs", ["actor_user_id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_audit_logs_organization_id"), "audit_logs", ["organization_id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_logs_resource_type"), "audit_logs", ["resource_type"], unique=False
    )
    op.create_index(
        "ix_audit_logs_org_created_at",
        "audit_logs",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_org_action",
        "audit_logs",
        ["organization_id", "action"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_org_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_org_created_at", table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_resource_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_organization_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
    sa.Enum(name="audit_action").drop(op.get_bind(), checkfirst=True)
