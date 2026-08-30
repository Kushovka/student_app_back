"""add max parent integration

Revision ID: a6b5c4d3e2f1
Revises: f5a6b7c8d9e0
Create Date: 2026-08-24 16:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a6b5c4d3e2f1"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("max_user_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("max_chat_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("max_link_code", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_max_user_id", "users", ["max_user_id"])
    op.create_unique_constraint("uq_users_max_link_code", "users", ["max_link_code"])


def downgrade() -> None:
    op.drop_constraint("uq_users_max_link_code", "users", type_="unique")
    op.drop_constraint("uq_users_max_user_id", "users", type_="unique")
    op.drop_column("users", "max_link_code")
    op.drop_column("users", "max_chat_id")
    op.drop_column("users", "max_user_id")
