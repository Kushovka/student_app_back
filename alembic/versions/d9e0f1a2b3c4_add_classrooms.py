"""add classrooms and register existing student classes

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
"""

from alembic import op
import sqlalchemy as sa


revision = "d9e0f1a2b3c4"
down_revision = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "classrooms",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("school_id", sa.String(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("class_letter", sa.String(length=1), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "grade", "class_letter", name="uq_classroom_school_grade_letter"),
    )
    op.create_index(op.f("ix_classrooms_id"), "classrooms", ["id"], unique=False)
    op.create_index(op.f("ix_classrooms_school_id"), "classrooms", ["school_id"], unique=False)
    op.execute(
        """
        INSERT INTO classrooms (id, school_id, grade, class_letter)
        SELECT md5(school_id || ':' || grade::text || ':' || class_letter), school_id, grade, class_letter
        FROM students
        GROUP BY school_id, grade, class_letter
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_classrooms_school_id"), table_name="classrooms")
    op.drop_index(op.f("ix_classrooms_id"), table_name="classrooms")
    op.drop_table("classrooms")
