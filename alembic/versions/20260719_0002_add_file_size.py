"""add file_size column

Revision ID: 20260719_0002
Revises: 20260517_0001
Create Date: 2026-07-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260719_0002"
down_revision: Union[str, None] = "20260517_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("files", sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("files", "file_size")
