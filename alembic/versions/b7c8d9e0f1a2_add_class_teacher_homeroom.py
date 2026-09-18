"""add class teacher homeroom

Revision ID: b7c8d9e0f1a2
Revises: a6b5c4d3e2f1
"""

from alembic import op
import sqlalchemy as sa


revision = "b7c8d9e0f1a2"
down_revision = "a6b5c4d3e2f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("homeroom_grade", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("homeroom_class_letter", sa.String(length=1), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "homeroom_class_letter")
    op.drop_column("users", "homeroom_grade")
