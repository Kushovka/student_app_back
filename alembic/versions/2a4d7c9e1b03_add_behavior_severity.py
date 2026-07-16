"""add behavior severity

Revision ID: 2a4d7c9e1b03
Revises: f13c8b7a9d21
Create Date: 2026-07-15 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "2a4d7c9e1b03"
down_revision: Union[str, Sequence[str], None] = "f13c8b7a9d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "behavior_records",
        sa.Column("severity", sa.String(), server_default="yellow", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("behavior_records", "severity")
