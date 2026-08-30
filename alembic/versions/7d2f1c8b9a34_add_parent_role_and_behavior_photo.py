"""add parent role and behavior photo

Revision ID: 7d2f1c8b9a34
Revises: 3c5e9b8a7f42
Create Date: 2026-07-26 11:40:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7d2f1c8b9a34"
down_revision: Union[str, Sequence[str], None] = "3c5e9b8a7f42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("behavior_records", sa.Column("photo_url", sa.String(), nullable=True))

    parent_hash = "$2b$12$17PhM58TIrOzSyb6cKJgFuuSLJVrHmjWhy6jJPZ70sXvVpx432IaW"
    op.execute(
        f"""
        INSERT INTO users (
            id, first_name, last_name, middle_name, email, hashed_password,
            role, is_blocked, school_id
        )
        VALUES (
            'test-parent-local', 'Тест', 'Родитель', 'Локальный',
            'parent01@example.com', '{parent_hash}', 'parent', false, 'school-demo-1'
        )
        ON CONFLICT (email) DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            middle_name = EXCLUDED.middle_name,
            hashed_password = EXCLUDED.hashed_password,
            role = EXCLUDED.role,
            is_blocked = EXCLUDED.is_blocked,
            school_id = EXCLUDED.school_id
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE id = 'test-parent-local'")
    op.drop_column("behavior_records", "photo_url")
