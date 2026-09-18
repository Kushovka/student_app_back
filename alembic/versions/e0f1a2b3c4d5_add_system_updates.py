"""add internal system-update notifications

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
"""

from alembic import op
import sqlalchemy as sa


revision = "e0f1a2b3c4d5"
down_revision = "d9e0f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("system_updates_seen_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "system_updates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_system_updates_published_at"),
        "system_updates",
        ["published_at"],
        unique=False,
    )
    op.execute(
        """
        INSERT INTO system_updates (id, title, description, published_at)
        VALUES (
            md5(random()::text || clock_timestamp()::text),
            'Системные уведомления',
            'В колокольчике теперь появляются сообщения о новых возможностях и изменениях в системе.',
            CURRENT_TIMESTAMP
        )
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_system_updates_published_at"), table_name="system_updates")
    op.drop_table("system_updates")
    op.drop_column("users", "system_updates_seen_at")
    op.drop_column("users", "created_at")
