"""remove behavior severity

Revision ID: f6e7d8c9b0a1
Revises: a1b2c3d4e5f6
Create Date: 2026-09-18 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "f6e7d8c9b0a1"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("behavior_records", "severity")


def downgrade() -> None:
    op.add_column(
        "behavior_records",
        sa.Column("severity", sa.String(), nullable=False, server_default="yellow"),
    )
