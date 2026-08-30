"""seed full test students

Revision ID: f5a6b7c8d9e0
Revises: e4b2c1a9d8f0
Create Date: 2026-08-23 12:20:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "e4b2c1a9d8f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FIRST_NAMES = [
    "Алексей",
    "Мария",
    "Иван",
    "София",
    "Даниил",
    "Анна",
    "Никита",
    "Полина",
    "Максим",
    "Ева",
]

LAST_NAMES = [
    "Соколов",
    "Иванова",
    "Петров",
    "Кузнецова",
    "Смирнов",
    "Попова",
    "Волков",
    "Новикова",
    "Васильев",
    "Федорова",
]

MIDDLE_NAMES = [
    "Андреевич",
    "Сергеевна",
    "Павлович",
    "Олеговна",
    "Игоревич",
    "Михайловна",
    "Алексеевич",
    "Романовна",
    "Денисович",
    "Викторовна",
]

CLASS_LETTERS = ["А", "Б", "В"]


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM teacher_assignments latin
        WHERE latin.teacher_id = 'test-teacher-local'
          AND latin.grade = 11
          AND latin.class_letter = 'A'
          AND EXISTS (
              SELECT 1
              FROM teacher_assignments cyrillic
              WHERE cyrillic.teacher_id = latin.teacher_id
                AND cyrillic.grade = latin.grade
                AND cyrillic.class_letter = 'А'
                AND cyrillic.subject = latin.subject
          )
        """
    )
    op.execute(
        """
        UPDATE teacher_assignments
        SET class_letter = 'А'
        WHERE teacher_id = 'test-teacher-local'
          AND grade = 11
          AND class_letter = 'A'
        """
    )

    rows = []
    for grade in range(1, 12):
        for letter in CLASS_LETTERS:
            letter_code = {"А": "a", "Б": "b", "В": "v"}[letter]
            for index in range(1, 11):
                first_name = FIRST_NAMES[index - 1]
                last_name = LAST_NAMES[index - 1]
                middle_name = MIDDLE_NAMES[index - 1]
                student_id = f"full-test-student-{grade}{letter_code}-{index:02d}"
                email = f"student{grade}{letter_code}{index:02d}@example.com"
                rows.append(
                    "('%s','%s','%s','%s','%s',%s,'%s','school-demo-1')"
                    % (
                        student_id,
                        first_name,
                        last_name,
                        middle_name,
                        email,
                        grade,
                        letter,
                    )
                )

    op.execute(
        f"""
        INSERT INTO students (
            id, first_name, last_name, middle_name, email, grade, class_letter, school_id
        )
        VALUES {", ".join(rows)}
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM students WHERE id LIKE 'full-test-student-%'")
