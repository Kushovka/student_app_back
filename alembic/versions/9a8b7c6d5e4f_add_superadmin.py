"""add superadmin

Revision ID: 9a8b7c6d5e4f
Revises: 7d2f1c8b9a34
Create Date: 2026-07-26 12:10:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, Sequence[str], None] = "7d2f1c8b9a34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    superadmin_hash = "$2b$12$cPTuPm3TUShLVrxZESx7du0yXxmuID2W9b2EiFkJ5WZ2b3zrPI1kG"
    op.execute(
        f"""
        INSERT INTO users (
            id, first_name, last_name, middle_name, email, hashed_password,
            role, is_blocked, school_id
        )
        VALUES (
            'test-superadmin-local', 'Кирилл', 'Владелец', 'Платформы',
            'superadmin@studentapp.ru', '{superadmin_hash}', 'superadmin', false, null
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
    op.execute("DELETE FROM users WHERE id = 'test-superadmin-local'")
