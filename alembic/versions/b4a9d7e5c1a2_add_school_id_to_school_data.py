"""add school id to school data

Revision ID: b4a9d7e5c1a2
Revises: 8f3bdccf1b61
Create Date: 2026-04-21 10:25:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b4a9d7e5c1a2"
down_revision: Union[str, Sequence[str], None] = "8f3bdccf1b61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("school_id", sa.String(), nullable=True))
    op.add_column("behavior_records", sa.Column("school_id", sa.String(), nullable=True))

    op.execute("UPDATE students SET school_id = 'school-demo-1' WHERE school_id IS NULL")
    op.execute(
        """
        UPDATE behavior_records
        SET school_id = students.school_id
        FROM students
        WHERE behavior_records.student_id = students.id
          AND behavior_records.school_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE behavior_records
        SET school_id = 'school-demo-1'
        WHERE school_id IS NULL
        """
    )

    op.alter_column("students", "school_id", nullable=False)
    op.alter_column("behavior_records", "school_id", nullable=False)

    op.create_foreign_key(
        op.f("fk_students_school_id_schools"),
        "students",
        "schools",
        ["school_id"],
        ["id"],
    )
    op.create_index(op.f("ix_students_school_id"), "students", ["school_id"])

    op.create_foreign_key(
        op.f("fk_behavior_records_school_id_schools"),
        "behavior_records",
        "schools",
        ["school_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_behavior_records_school_id"), "behavior_records", ["school_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_behavior_records_school_id"), table_name="behavior_records")
    op.drop_constraint(
        op.f("fk_behavior_records_school_id_schools"),
        "behavior_records",
        type_="foreignkey",
    )
    op.drop_column("behavior_records", "school_id")

    op.drop_index(op.f("ix_students_school_id"), table_name="students")
    op.drop_constraint(
        op.f("fk_students_school_id_schools"), "students", type_="foreignkey"
    )
    op.drop_column("students", "school_id")
