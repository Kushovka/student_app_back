"""add teacher assignments

Revision ID: e4b2c1a9d8f0
Revises: d1e2f3a4b5c6
Create Date: 2026-08-23 12:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e4b2c1a9d8f0"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teacher_assignments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("teacher_id", sa.String(), nullable=False),
        sa.Column("school_id", sa.String(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("class_letter", sa.String(length=1), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("teacher_id", "grade", "class_letter", "subject", name="uq_teacher_assignment"),
    )
    op.create_index(op.f("ix_teacher_assignments_id"), "teacher_assignments", ["id"])
    op.create_index(op.f("ix_teacher_assignments_school_id"), "teacher_assignments", ["school_id"])
    op.create_index(op.f("ix_teacher_assignments_teacher_id"), "teacher_assignments", ["teacher_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_teacher_assignments_teacher_id"), table_name="teacher_assignments")
    op.drop_index(op.f("ix_teacher_assignments_school_id"), table_name="teacher_assignments")
    op.drop_index(op.f("ix_teacher_assignments_id"), table_name="teacher_assignments")
    op.drop_table("teacher_assignments")
