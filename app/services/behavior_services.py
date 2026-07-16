import os
import smtplib
from email.message import EmailMessage

from app.models.student import Student
from app.models.user import User


def send_behavior_email(
    student: Student,
    teacher: User,
    subject: str,
    reasons: list[str],
    comment: str | None,
):
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not smtp_user or not smtp_password:
        return

    email = EmailMessage()
    email["From"] = smtp_user
    email["To"] = student.email
    email["Subject"] = f"Замечание по предмету {subject}"

    reasons_text = "\n".join([f"• {r}" for r in reasons])

    comment_block = ""
    if comment:
        comment_block = f"\nКомментарий:\n{comment}\n"

    teacher_name = " ".join(
        part
        for part in (teacher.last_name, teacher.first_name, teacher.middle_name)
        if part
    )

    email.set_content(
        f"""
Здравствуйте!

Ученик: {student.last_name} {student.first_name}
Класс: {student.grade}{student.class_letter}

Предмет: {subject}

Причины:
{reasons_text}
{comment_block}

С уважением,
{teacher_name}
"""
    )

    with smtplib.SMTP("smtp.yandex.ru", 587, timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(email)


def send_digest_email(student: Student, records) -> None:
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not smtp_user or not smtp_password:
        return

    email = EmailMessage()
    email["From"] = smtp_user
    email["To"] = student.email
    email["Subject"] = "Дайджест замечаний"

    lines = []
    for record in records:
        reasons_text = ", ".join(record.reasons or [])
        lines.append(
            f"- {record.created_at.strftime('%d.%m.%Y')} | "
            f"{record.subject} | {record.severity}: {reasons_text}"
        )

    email.set_content(
        f"""
Здравствуйте!

Дайджест замечаний ученика: {student.last_name} {student.first_name}
Класс: {student.grade}{student.class_letter}

{chr(10).join(lines)}

С уважением,
Школьный Дисциплинарный Контроль
"""
    )

    with smtplib.SMTP("smtp.yandex.ru", 587, timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(email)
