"""add user block flag

Revision ID: f13c8b7a9d21
Revises: c7d9a1e4b8f2
Create Date: 2026-05-01 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f13c8b7a9d21"
down_revision: Union[str, Sequence[str], None] = "c7d9a1e4b8f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_blocked", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_blocked")
