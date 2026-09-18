"""add notification queue

Revision ID: 3c5e9b8a7f42
Revises: 2a4d7c9e1b03
Create Date: 2026-07-15 00:10:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "3c5e9b8a7f42"
down_revision: Union[str, Sequence[str], None] = "2a4d7c9e1b03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_queue",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("behavior_record_id", sa.String(), nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("school_id", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["behavior_record_id"], ["behavior_records.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_queue_behavior_record_id"), "notification_queue", ["behavior_record_id"])
    op.create_index(op.f("ix_notification_queue_school_id"), "notification_queue", ["school_id"])
    op.create_index(op.f("ix_notification_queue_student_id"), "notification_queue", ["student_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_queue_student_id"), table_name="notification_queue")
    op.drop_index(op.f("ix_notification_queue_school_id"), table_name="notification_queue")
    op.drop_index(op.f("ix_notification_queue_behavior_record_id"), table_name="notification_queue")
    op.drop_table("notification_queue")
