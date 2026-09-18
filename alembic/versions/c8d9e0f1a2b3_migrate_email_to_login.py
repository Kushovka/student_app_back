"""migrate email accounts to logins and remove legacy notifications

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
"""

from alembic import op
import sqlalchemy as sa


revision = "c8d9e0f1a2b3"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("login", sa.String(), nullable=True))

    connection = op.get_bind()
    users = connection.execute(sa.text("SELECT id, email FROM users ORDER BY id")).mappings()
    used_logins: set[str] = set()
    for user in users:
        base = (user["email"] or "user").split("@", 1)[0].strip().lower() or "user"
        login = base
        suffix = 2
        while login in used_logins:
            login = f"{base}{suffix}"
            suffix += 1
        used_logins.add(login)
        connection.execute(
            sa.text("UPDATE users SET login = :login WHERE id = :id"),
            {"login": login, "id": user["id"]},
        )

    op.alter_column("users", "login", nullable=False)
    op.create_index(op.f("ix_users_login"), "users", ["login"], unique=True)
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_column("users", "email")
    op.drop_column("students", "email")
    op.drop_table("notification_queue")


def downgrade() -> None:
    op.create_table(
        "notification_queue",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("behavior_record_id", sa.String(), nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("school_id", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
    )
    op.add_column("students", sa.Column("email", sa.String(), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    op.execute("UPDATE users SET email = login || '@legacy.local'")
    op.alter_column("users", "email", nullable=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.drop_index(op.f("ix_users_login"), table_name="users")
    op.drop_column("users", "login")
