"""retain schools revision without demo data

Revision ID: 8f3bdccf1b61
Revises: 6b27f8f3e97f
Create Date: 2026-04-21 10:12:00
"""

from typing import Sequence, Union


revision: str = "8f3bdccf1b61"
down_revision: Union[str, Sequence[str], None] = "6b27f8f3e97f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
