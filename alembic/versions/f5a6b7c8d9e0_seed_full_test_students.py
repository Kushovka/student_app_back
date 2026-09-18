"""retain test-data revision without inserting test data

Revision ID: f5a6b7c8d9e0
Revises: e4b2c1a9d8f0
Create Date: 2026-08-23 12:20:00
"""

from typing import Sequence, Union


revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "e4b2c1a9d8f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
