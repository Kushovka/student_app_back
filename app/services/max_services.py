import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.models.behavior_record import BehaviorRecord
from app.models.student import Student
from app.models.user import User


logger = logging.getLogger(__name__)


def _is_enabled() -> bool:
    return os.getenv("MAX_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _get_config() -> tuple[str, str] | None:
    if not _is_enabled():
        return None

    token = os.getenv("MAX_BOT_TOKEN")
    if not token:
        return None

    api_url = os.getenv("MAX_API_URL") or "https://platform-api2.max.ru"
    return api_url.rstrip("/"), token


def get_max_bot_username() -> str | None:
    value = os.getenv("MAX_BOT_USERNAME")
    return value.strip().lstrip("@") if value else None


def send_max_text(user_id: str, text: str) -> bool:
    config = _get_config()
    if not config or not user_id:
        return False

    api_url, token = config
    query = urlencode({"user_id": user_id})
    request = Request(
        f"{api_url}/messages?{query}",
        data=json.dumps({"text": text}, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": token,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError):
        logger.exception("Failed to send MAX message to user_id=%s", user_id)
        return False


def build_behavior_max_text(
    student: Student,
    teacher: User,
    record: BehaviorRecord,
) -> str:
    teacher_name = " ".join(
        part
        for part in (teacher.last_name, teacher.first_name, teacher.middle_name)
        if part
    )
    reasons = "\n".join(f"- {reason}" for reason in (record.reasons or []))
    comment = f"\n\nКомментарий:\n{record.comment}" if record.comment else ""
    photo = "\n\nФото прикреплено в школьном кабинете." if record.photo_url else ""

    return (
        "Новое замечание\n\n"
        f"Ученик: {student.last_name} {student.first_name} {student.middle_name}\n"
        f"Класс: {student.grade}{student.class_letter}\n"
        f"Урок: {record.subject}\n\n"
        f"Причины:\n{reasons}"
        f"{comment}"
        f"{photo}\n\n"
        f"Отправитель: {teacher_name}"
    )


def send_behavior_max_message(
    student: Student,
    teacher: User,
    record: BehaviorRecord,
    max_user_ids: list[str],
) -> int:
    text = build_behavior_max_text(student, teacher, record)
    sent = 0
    for user_id in max_user_ids:
        if send_max_text(user_id, text):
            sent += 1
    return sent
