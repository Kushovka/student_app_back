import json
import logging
import mimetypes
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
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


def get_public_photo_url(photo_url: str | None) -> str | None:
    """Возвращает публичную HTTPS-ссылку на фото для вложения MAX."""
    if not photo_url:
        return None
    if photo_url.startswith(("https://", "http://")):
        return photo_url

    public_api_url = (os.getenv("PUBLIC_API_URL") or "").rstrip("/")
    if not public_api_url:
        return None
    return f"{public_api_url}/{photo_url.lstrip('/')}"


def send_max_text(
    user_id: str,
    text: str,
    attachments: list[dict[str, Any]] | None = None,
) -> bool:
    config = _get_config()
    if not config or not user_id:
        return False

    api_url, token = config
    query = urlencode({"user_id": user_id})
    payload: dict[str, Any] = {"text": text}
    if attachments:
        payload["attachments"] = attachments

    request = Request(
        f"{api_url}/messages?{query}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": token,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except HTTPError as error:
        logger.warning(
            "MAX message rejected for user_id=%s, status=%s, body=%s",
            user_id,
            error.code,
            error.read().decode("utf-8", errors="replace")[:500],
        )
        return False
    except (URLError, TimeoutError):
        logger.exception("Failed to send MAX message to user_id=%s", user_id)
        return False


def upload_max_image(photo_url: str | None) -> str | None:
    """Загружает локальное фото замечания в MAX и возвращает токен вложения."""
    config = _get_config()
    if not config or not photo_url or not photo_url.startswith("/uploads/"):
        return None

    relative_path = photo_url.lstrip("/")
    source = (Path.cwd() / relative_path).resolve()
    uploads_dir = (Path.cwd() / "uploads").resolve()
    if uploads_dir not in source.parents or not source.is_file():
        logger.warning("MAX image source is unavailable: %s", photo_url)
        return None

    if source.stat().st_size > 50 * 1024 * 1024:
        logger.warning("MAX image is larger than 50 MB: %s", photo_url)
        return None

    api_url, token = config
    upload_request = Request(
        f"{api_url}/uploads?type=image",
        headers={"Authorization": token},
        method="POST",
    )
    try:
        with urlopen(upload_request, timeout=15) as response:
            upload_metadata = json.loads(response.read().decode("utf-8"))
        upload_url = upload_metadata.get("url")
        if not upload_url:
            logger.warning("MAX did not return an upload URL for %s", photo_url)
            return None

        token_from_upload_url = parse_qs(urlparse(upload_url).query).get(
            "token", [None]
        )[0]

        boundary = f"----school-control-{uuid.uuid4().hex}"
        mime_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        body = b"".join(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="data"; '
                    f'filename="{source.name}"\r\n'
                ).encode(),
                f"Content-Type: {mime_type}\r\n\r\n".encode(),
                source.read_bytes(),
                b"\r\n",
                f"--{boundary}--\r\n".encode(),
            ]
        )
        file_request = Request(
            upload_url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urlopen(file_request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        attachment_token = _find_max_attachment_token(result) or token_from_upload_url
        if not attachment_token:
            logger.warning(
                "MAX did not return an image token for %s; response keys=%s",
                photo_url,
                sorted(result.keys()),
            )
        return attachment_token
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        logger.exception("Failed to upload MAX image: %s", photo_url)
        return None


def _find_max_attachment_token(value: Any) -> str | None:
    """MAX может вернуть токен как напрямую, так и внутри photos/data."""
    if isinstance(value, dict):
        token = value.get("token")
        if isinstance(token, str) and token:
            return token
        for nested_value in value.values():
            nested_token = _find_max_attachment_token(nested_value)
            if nested_token:
                return nested_token
    elif isinstance(value, list):
        for item in value:
            nested_token = _find_max_attachment_token(item)
            if nested_token:
                return nested_token
    return None


def build_behavior_max_text(
    student: Student,
    teacher: User,
    record: BehaviorRecord,
    photo_attached: bool = False,
) -> str:
    teacher_name = " ".join(
        part
        for part in (teacher.last_name, teacher.first_name, teacher.middle_name)
        if part
    )
    reasons = "\n".join(f"- {reason}" for reason in (record.reasons or []))
    comment = f"\n\nКомментарий:\n{record.comment}" if record.comment else ""
    photo = "\n\nФото прикреплено к сообщению." if photo_attached else ""

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
    image_token = upload_max_image(record.photo_url)
    text = build_behavior_max_text(
        student,
        teacher,
        record,
        photo_attached=bool(image_token),
    )
    image_attachments = (
        [{"type": "image", "payload": {"token": image_token}}]
        if image_token
        else None
    )
    sent = 0
    for user_id in max_user_ids:
        if send_max_text(user_id, text):
            sent += 1
            if image_attachments:
                for attempt in range(3):
                    if send_max_text(user_id, "Фото к замечанию", image_attachments):
                        break
                    time.sleep(0.7 * (attempt + 1))
    return sent
