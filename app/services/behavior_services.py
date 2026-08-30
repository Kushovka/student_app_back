import os
import smtplib
from email.message import EmailMessage
from mimetypes import guess_type
from pathlib import Path

from app.models.student import Student
from app.models.user import User


def _get_smtp_config() -> tuple[str, int, str, str, str] | None:
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not smtp_user or not smtp_password:
        return None

    smtp_host = os.getenv("SMTP_HOST") or "smtp.yandex.ru"
    smtp_port = int(os.getenv("SMTP_PORT") or "587")
    smtp_from = os.getenv("SMTP_FROM") or smtp_user
    return smtp_host, smtp_port, smtp_user, smtp_password, smtp_from


def _send_email(email: EmailMessage) -> None:
    config = _get_smtp_config()
    if not config:
        return

    smtp_host, smtp_port, smtp_user, smtp_password, _ = config
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as smtp:
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(email)
        return

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(email)


def _attach_photo(email: EmailMessage, photo_url: str | None, filename_prefix: str) -> None:
    if not photo_url:
        return

    photo_path = Path(photo_url.lstrip("/"))
    if not photo_path.is_file():
        return

    content_type, _ = guess_type(photo_path.name)
    if content_type:
        maintype, subtype = content_type.split("/", 1)
    else:
        maintype, subtype = "application", "octet-stream"

    email.add_attachment(
        photo_path.read_bytes(),
        maintype=maintype,
        subtype=subtype,
        filename=f"{filename_prefix}{photo_path.suffix}",
    )


def send_behavior_email(
    student: Student,
    teacher: User,
    subject: str,
    reasons: list[str],
    comment: str | None,
    recipients: list[str] | None = None,
    photo_url: str | None = None,
):
    config = _get_smtp_config()
    if not config:
        return
    _, _, _, _, smtp_from = config

    email = EmailMessage()
    email["From"] = smtp_from
    target_emails = recipients or ([student.email] if student.email else [])
    if not target_emails:
        return

    email["To"] = ", ".join(target_emails)
    email["Subject"] = f"Замечание по предмету {subject}"

    reasons_text = "\n".join([f"• {r}" for r in reasons])

    comment_block = ""
    if comment:
        comment_block = f"\nКомментарий:\n{comment}\n"
    photo_block = "\nФото прикреплено к письму.\n" if photo_url else ""

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
{photo_block}

С уважением,
{teacher_name}
"""
    )

    _attach_photo(email, photo_url, "behavior-photo")
    _send_email(email)


def send_digest_email(student: Student, records, recipients: list[str] | None = None) -> None:
    config = _get_smtp_config()
    if not config:
        return
    _, _, _, _, smtp_from = config

    email = EmailMessage()
    email["From"] = smtp_from
    target_emails = recipients or ([student.email] if student.email else [])
    if not target_emails:
        return

    email["To"] = ", ".join(target_emails)
    email["Subject"] = "Сводка замечаний"

    lines = []
    for record in records:
        reasons_text = ", ".join(record.reasons or [])
        photo_text = " | фото прикреплено" if record.photo_url else ""
        lines.append(
            f"- {record.created_at.strftime('%d.%m.%Y')} | "
            f"{record.subject}: {reasons_text}{photo_text}"
        )

    email.set_content(
        f"""
Здравствуйте!

Сводка замечаний ученика: {student.last_name} {student.first_name}
Класс: {student.grade}{student.class_letter}

{chr(10).join(lines)}

С уважением,
Школьный Дисциплинарный Контроль
"""
    )

    for index, record in enumerate(records, start=1):
        _attach_photo(email, record.photo_url, f"digest-photo-{index}")
    _send_email(email)
