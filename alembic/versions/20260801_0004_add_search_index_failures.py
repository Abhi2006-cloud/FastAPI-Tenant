"""add search_index_failures table

Revision ID: 20260801_0004
Revises: 20260721_0003
Create Date: 2026-08-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260801_0004"
down_revision: Union[str, None] = "20260721_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "search_index_failures",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=True),
        sa.Column("index_name", sa.String(length=255), nullable=False),
        sa.Column("document_id", sa.String(length=255), nullable=False),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("search_index_failures")
