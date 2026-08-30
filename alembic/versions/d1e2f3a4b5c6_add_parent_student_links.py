"""add parent student links

Revision ID: d1e2f3a4b5c6
Revises: 9a8b7c6d5e4f
Create Date: 2026-08-23 15:20:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "9a8b7c6d5e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parent_students",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("parent_id", sa.String(), nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("relationship", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "student_id", name="uq_parent_student"),
    )
    op.create_index(op.f("ix_parent_students_id"), "parent_students", ["id"])
    op.create_index("ix_parent_students_parent_id", "parent_students", ["parent_id"])
    op.create_index("ix_parent_students_student_id", "parent_students", ["student_id"])

    op.execute(
        """
        INSERT INTO parent_students (id, parent_id, student_id, relationship)
        SELECT
            'link-' || u.id || '-' || s.id,
            u.id,
            s.id,
            'Родитель'
        FROM students s
        JOIN users u
          ON lower(u.email) = lower(s.email)
         AND u.school_id = s.school_id
         AND u.role = 'parent'
        ON CONFLICT (parent_id, student_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_parent_students_student_id", table_name="parent_students")
    op.drop_index("ix_parent_students_parent_id", table_name="parent_students")
    op.drop_index(op.f("ix_parent_students_id"), table_name="parent_students")
    op.drop_table("parent_students")
