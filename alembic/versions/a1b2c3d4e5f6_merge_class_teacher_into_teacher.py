"""merge class teacher role into teacher

Revision ID: a1b2c3d4e5f6
Revises: e0f1a2b3c4d5
Create Date: 2026-09-09 12:00:00
"""

from alembic import op


revision = "a1b2c3d4e5f6"
down_revision = "e0f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Homeroom data is already stored on users, so changing the role preserves
    # each class teacher's class and MAX connection without duplicating accounts.
    op.execute("UPDATE users SET role = 'teacher' WHERE role = 'class_teacher'")


def downgrade() -> None:
    # The previous standalone role can be restored only for teachers with a
    # homeroom assignment. Other teachers remain regular teachers.
    op.execute(
        """
        UPDATE users
        SET role = 'class_teacher'
        WHERE role = 'teacher'
          AND homeroom_grade IS NOT NULL
          AND homeroom_class_letter IS NOT NULL
        """
    )
