"""add parent role and behavior photo

Revision ID: 7d2f1c8b9a34
Revises: 3c5e9b8a7f42
Create Date: 2026-07-26 11:40:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7d2f1c8b9a34"
down_revision: Union[str, Sequence[str], None] = "3c5e9b8a7f42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("behavior_records", sa.Column("photo_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("behavior_records", "photo_url")
