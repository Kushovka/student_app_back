"""add schools

Revision ID: 6b27f8f3e97f
Revises: 83308f92c3f5
Create Date: 2026-04-21 10:02:26.628674
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "6b27f8f3e97f"
down_revision: Union[str, Sequence[str], None] = "83308f92c3f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schools_id"), "schools", ["id"], unique=False)

    op.add_column("users", sa.Column("school_id", sa.String(), nullable=True))
    op.create_foreign_key(
        op.f("fk_users_school_id_schools"), "users", "schools", ["school_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_users_school_id_schools"), "users", type_="foreignkey")
    op.drop_column("users", "school_id")
    op.drop_index(op.f("ix_schools_id"), table_name="schools")
    op.drop_table("schools")
