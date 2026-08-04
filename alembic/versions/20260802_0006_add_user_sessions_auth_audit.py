"""add user_sessions and auth_audit_logs tables

Revision ID: 20260802_0006
Revises: 20260802_0005
Create Date: 2026-08-02 00:06:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260802_0006"
down_revision: Union[str, None] = "20260802_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── user_sessions ────────────────────────────────────────────────────────
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # SHA-256 hex of the raw refresh token — never store plaintext
        sa.Column("refresh_token_hash", sa.String(64), nullable=False, unique=True),
        # Device / browser info
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("platform", sa.String(128), nullable=True),
        sa.Column("browser", sa.String(128), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Indexes on user_sessions
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_index(
        "ix_user_sessions_user_revoked",
        "user_sessions",
        ["user_id", "revoked_at"],
    )
    op.create_index(
        "ix_user_sessions_is_revoked", "user_sessions", ["is_revoked"]
    )
    op.create_index(
        "ix_user_sessions_last_used_at", "user_sessions", ["last_used_at"]
    )

    # ── auth_audit_logs ──────────────────────────────────────────────────────
    op.create_table(
        "auth_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "event_type",
            sa.String(64),
            nullable=False,
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Indexes on auth_audit_logs
    op.create_index(
        "ix_auth_audit_logs_user_created",
        "auth_audit_logs",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_auth_audit_logs_event_type", "auth_audit_logs", ["event_type"]
    )
    op.create_index(
        "ix_auth_audit_logs_created_at", "auth_audit_logs", ["created_at"]
    )
    op.create_index(
        "ix_auth_audit_logs_user_id", "auth_audit_logs", ["user_id"]
    )


def downgrade() -> None:
    # Drop auth_audit_logs first (no dependents)
    op.drop_index("ix_auth_audit_logs_user_id", table_name="auth_audit_logs")
    op.drop_index("ix_auth_audit_logs_created_at", table_name="auth_audit_logs")
    op.drop_index("ix_auth_audit_logs_event_type", table_name="auth_audit_logs")
    op.drop_index("ix_auth_audit_logs_user_created", table_name="auth_audit_logs")
    op.drop_table("auth_audit_logs")

    # Drop user_sessions
    op.drop_index("ix_user_sessions_last_used_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_is_revoked", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_revoked", table_name="user_sessions")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
