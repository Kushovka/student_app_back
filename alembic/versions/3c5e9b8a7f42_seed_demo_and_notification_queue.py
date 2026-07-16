"""seed demo data and notification queue

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
    op.create_index(
        op.f("ix_notification_queue_behavior_record_id"),
        "notification_queue",
        ["behavior_record_id"],
    )
    op.create_index(
        op.f("ix_notification_queue_school_id"), "notification_queue", ["school_id"]
    )
    op.create_index(
        op.f("ix_notification_queue_student_id"), "notification_queue", ["student_id"]
    )

    admin_hash = "$2b$12$1LVtIY6JVORSLdmJhFDVlOjafd2nnUV/f2i0QK/GY/h5/UrHg5rhC"
    teacher_hash = "$2b$12$.kW8I.4VMKggbXMoApsniu3IsEohg.iBUAGEEPq7gQCgJAshwjxDO"

    op.execute(
        f"""
        INSERT INTO users (
            id, first_name, last_name, middle_name, email, hashed_password,
            role, is_blocked, school_id
        )
        VALUES
            (
                'test-admin-local', 'Тест', 'Админ', 'Локальный',
                'admin@studentapp.ru', '{admin_hash}', 'admin', false, 'school-demo-1'
            ),
            (
                'test-teacher-local', 'Тест', 'Учитель', 'Локальный',
                'teacher@studentapp.ru', '{teacher_hash}', 'teacher', false, 'school-demo-1'
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

    students = [
        ("demo-student-7a-01", "Иван", "Иванов", "Сергеевич", "parent01@example.com", 7, "А"),
        ("demo-student-7a-02", "Мария", "Петрова", "Андреевна", "parent02@example.com", 7, "А"),
        ("demo-student-7a-03", "Артём", "Сидоров", "Олегович", "parent03@example.com", 7, "А"),
        ("demo-student-7a-04", "София", "Кузнецова", "Ильинична", "parent04@example.com", 7, "А"),
        ("demo-student-7a-05", "Даниил", "Смирнов", "Павлович", "parent05@example.com", 7, "А"),
        ("demo-student-7b-01", "Ева", "Попова", "Михайловна", "parent06@example.com", 7, "Б"),
        ("demo-student-7b-02", "Максим", "Васильев", "Игоревич", "parent07@example.com", 7, "Б"),
        ("demo-student-7b-03", "Полина", "Новикова", "Романовна", "parent08@example.com", 7, "Б"),
        ("demo-student-7b-04", "Кирилл", "Морозов", "Денисович", "parent09@example.com", 7, "Б"),
        ("demo-student-7b-05", "Анна", "Фёдорова", "Викторовна", "parent10@example.com", 7, "Б"),
        ("demo-student-8a-01", "Никита", "Волков", "Алексеевич", "parent11@example.com", 8, "А"),
        ("demo-student-8a-02", "Алина", "Соколова", "Евгеньевна", "parent12@example.com", 8, "А"),
        ("demo-student-8a-03", "Матвей", "Павлов", "Станиславович", "parent13@example.com", 8, "А"),
        ("demo-student-8a-04", "Варвара", "Зайцева", "Петровна", "parent14@example.com", 8, "А"),
        ("demo-student-8a-05", "Глеб", "Орлов", "Николаевич", "parent15@example.com", 8, "А"),
    ]
    values = ",\n".join(
        "('%s','%s','%s','%s','%s',%s,'%s','school-demo-1')"
        % row
        for row in students
    )
    op.execute(
        f"""
        INSERT INTO students (
            id, first_name, last_name, middle_name, email, grade, class_letter, school_id
        )
        VALUES {values}
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM students WHERE id LIKE 'demo-student-%'")
    op.execute("DELETE FROM users WHERE id IN ('test-admin-local', 'test-teacher-local')")
    op.drop_index(op.f("ix_notification_queue_student_id"), table_name="notification_queue")
    op.drop_index(op.f("ix_notification_queue_school_id"), table_name="notification_queue")
    op.drop_index(
        op.f("ix_notification_queue_behavior_record_id"),
        table_name="notification_queue",
    )
    op.drop_table("notification_queue")
