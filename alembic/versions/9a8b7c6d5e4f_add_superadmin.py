"""retain superadmin revision without creating an account

Revision ID: 9a8b7c6d5e4f
Revises: 7d2f1c8b9a34
Create Date: 2026-07-26 12:10:00
"""

from typing import Sequence, Union


revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, Sequence[str], None] = "7d2f1c8b9a34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
