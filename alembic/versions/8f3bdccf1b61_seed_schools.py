"""seed schools

Revision ID: 8f3bdccf1b61
Revises: 6b27f8f3e97f
Create Date: 2026-04-21 10:12:00
"""

from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "8f3bdccf1b61"
down_revision: Union[str, Sequence[str], None] = "6b27f8f3e97f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


schools_table = sa.table(
    "schools",
    sa.column("id", sa.String),
    sa.column("name", sa.String),
    sa.column("city", sa.String),
    sa.column("created_at", sa.DateTime),
)


def upgrade() -> None:
    created_at = datetime.utcnow()
    op.bulk_insert(
        schools_table,
        [
            {
                "id": "school-demo-1",
                "name": "Школа 1",
                "city": "Екатеринбург",
                "created_at": created_at,
            },
            {
                "id": "school-demo-2",
                "name": "Школа 2",
                "city": "Екатеринбург",
                "created_at": created_at,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schools WHERE id IN ('school-demo-1', 'school-demo-2')"
    )
