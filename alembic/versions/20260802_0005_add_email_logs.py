"""add email_logs table

Revision ID: 20260802_0005
Revises: 20260801_0004
Create Date: 2026-08-02 00:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260802_0005"
down_revision: Union[str, None] = "20260801_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure Enum type is created safely
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'emailstatus') THEN "
        "CREATE TYPE emailstatus AS ENUM ('QUEUED', 'PROCESSING', 'SENT', 'FAILED', 'CANCELLED'); "
        "END IF; END $$;"
    )
    email_status_enum = postgresql.ENUM("QUEUED", "PROCESSING", "SENT", "FAILED", "CANCELLED", name="emailstatus", create_type=False)

    op.create_table(
        "email_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="console"),
        sa.Column("template_name", sa.String(length=100), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("status", email_status_enum, nullable=False, server_default="QUEUED"),

        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("rq_job_id", sa.String(length=255), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_email_logs_organization_id", "email_logs", ["organization_id"])
    op.create_index("ix_email_logs_recipient_email", "email_logs", ["recipient_email"])
    op.create_index("ix_email_logs_status", "email_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_email_logs_status", table_name="email_logs")
    op.drop_index("ix_email_logs_recipient_email", table_name="email_logs")
    op.drop_index("ix_email_logs_organization_id", table_name="email_logs")
    op.drop_table("email_logs")
    op.execute("DROP TYPE IF EXISTS emailstatus")
