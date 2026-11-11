"""enum audit and values migration

Revision ID: 20260802_0009
Revises: 20260802_0008
Create Date: 2026-08-02 00:09:00.000000

Enum Audit Findings:
- AuditAction: Defined in 20260721_0003 with native_enum=False; creates VARCHAR(64) on Postgres.
- InvitationStatus: Defined in 20260517_0001 with native_enum=False; creates VARCHAR(32) on Postgres.
- MembershipRole: Defined in 20260517_0001 with native_enum=False; creates VARCHAR(6) on Postgres.
- AuthEventType: Defined in 20260802_0006 as sa.String(64) on Postgres. Contains PASSWORD_CHANGE.
- EmailStatus: Defined in 20260802_0005 as native Postgres enum 'emailstatus' ('QUEUED', 'PROCESSING', 'SENT', 'FAILED', 'CANCELLED').

This migration ensures that if any Postgres instance was created with native enum types
for audit_action or invitation_status, the Phase 2 values are safely added via ALTER TYPE ADD VALUE.
On SQLite and instances using standard VARCHAR columns, this is a safe no-op.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260802_0009"
down_revision: Union[str, None] = "20260802_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Check for native enum types in postgres
    # In Postgres, ALTER TYPE ... ADD VALUE cannot run inside a multi-statement transaction
    with op.get_context().autocommit_block():
        conn = op.get_bind()
        
        # Check audit_action / auditaction
        for type_name in ("audit_action", "auditaction"):
            res = conn.execute(
                sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
                {"name": type_name},
            ).scalar()
            if res:
                for val in (
                    "PLAN_CHANGED",
                    "UPGRADE_REQUESTED",
                    "INVITATION_REVOKED",
                    "MEMBER_LEFT",
                    "ORGANIZATION_DELETED",
                ):
                    try:
                        conn.execute(
                            sa.text(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '{val}'")
                        )
                    except Exception:
                        pass

        # Check invitation_status / invitationstatus
        for type_name in ("invitation_status", "invitationstatus"):
            res = conn.execute(
                sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
                {"name": type_name},
            ).scalar()
            if res:
                try:
                    conn.execute(
                        sa.text(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS 'revoked'")
                    )
                except Exception:
                    pass


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type (ALTER TYPE DROP VALUE)
    pass
