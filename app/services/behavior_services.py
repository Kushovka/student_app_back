import os
import smtplib
from email.message import EmailMessage

from app.models.student import Student


def send_behavior_email(
    student: Student, subject: str, reasons: list[str], comment: str | None
):
    email = EmailMessage()
    email["From"] = os.getenv("SMTP_USER")
    email["To"] = student.email
    email["Subject"] = f"Замечание по предмету {subject}"

    reasons_text = "\n".join([f"• {r}" for r in reasons])

    comment_block = ""
    if comment:
        comment_block = f"\nКомментарий:\n{comment}\n"

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
Учитель
"""
    )

    with smtplib.SMTP("smtp.yandex.ru", 587, timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
        smtp.send_message(email)
