"""add user roles

Revision ID: c7d9a1e4b8f2
Revises: b4a9d7e5c1a2
Create Date: 2026-04-22 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c7d9a1e4b8f2"
down_revision: Union[str, Sequence[str], None] = "b4a9d7e5c1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(), server_default="teacher", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
