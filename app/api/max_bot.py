import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.max_bot import MaxLinkCodeOut, MaxWebhookOut
from app.services.max_services import get_max_bot_username, send_max_text


router = APIRouter(prefix="/max", tags=["MAX"])


def _new_link_code() -> str:
    return secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:12]


def _extract_text(payload: dict[str, Any]) -> str:
    message = payload.get("message") or payload.get("update") or payload
    body = message.get("body") if isinstance(message, dict) else None
    if isinstance(body, dict) and isinstance(body.get("text"), str):
        return body["text"].strip()
    if isinstance(message, dict) and isinstance(message.get("text"), str):
        return message["text"].strip()
    return ""


def _extract_user_id(payload: dict[str, Any]) -> str | None:
    message = payload.get("message") or payload.get("update") or payload
    candidates = [
        payload.get("user_id"),
        payload.get("sender", {}).get("user_id") if isinstance(payload.get("sender"), dict) else None,
        message.get("sender", {}).get("user_id") if isinstance(message, dict) and isinstance(message.get("sender"), dict) else None,
        message.get("from", {}).get("user_id") if isinstance(message, dict) and isinstance(message.get("from"), dict) else None,
    ]
    for value in candidates:
        if value is not None:
            return str(value)
    return None


def _extract_chat_id(payload: dict[str, Any]) -> str | None:
    message = payload.get("message") or payload.get("update") or payload
    recipient = message.get("recipient") if isinstance(message, dict) else None
    candidates = [
        payload.get("chat_id"),
        recipient.get("chat_id") if isinstance(recipient, dict) else None,
        message.get("chat_id") if isinstance(message, dict) else None,
    ]
    for value in candidates:
        if value is not None:
            return str(value)
    return None


def _extract_link_code(text: str) -> str:
    if not text:
        return ""
    parts = text.split()
    if parts[0].lower() == "/start" and len(parts) > 1:
        return parts[1].strip()
    return parts[0].strip()


@router.get("/link-code", response_model=MaxLinkCodeOut)
def get_link_code(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "parent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MAX linking is available for parents only",
        )

    if not current_user.max_link_code:
        code = _new_link_code()
        while db.query(User.id).filter(User.max_link_code == code).first():
            code = _new_link_code()
        current_user.max_link_code = code
        db.add(current_user)
        db.commit()
        db.refresh(current_user)

    return {
        "code": current_user.max_link_code,
        "bot_username": get_max_bot_username(),
        "connected": current_user.max_connected,
    }


@router.post("/webhook", response_model=MaxWebhookOut)
async def max_webhook(request: Request, db: Session = Depends(get_db)):
    secret = request.app.extra.get("max_webhook_secret")
    if secret and request.headers.get("X-Max-Webhook-Secret") != secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    payload = await request.json()
    text = _extract_text(payload)
    code = _extract_link_code(text)
    max_user_id = _extract_user_id(payload)
    max_chat_id = _extract_chat_id(payload)

    if not code or not max_user_id:
        return {"ok": False, "detail": "No link code or MAX user id found"}

    parent = (
        db.query(User)
        .filter(
            User.role == "parent",
            User.max_link_code == code,
            User.is_blocked.is_(False),
        )
        .first()
    )
    if not parent:
        send_max_text(max_user_id, "Код не найден. Проверьте код в профиле родителя.")
        return {"ok": False, "detail": "Parent link code not found"}

    parent.max_user_id = max_user_id
    parent.max_chat_id = max_chat_id
    parent.max_link_code = None
    db.add(parent)
    db.commit()

    send_max_text(max_user_id, "MAX подключен к родительскому кабинету.")
    return {"ok": True, "detail": "Parent linked"}
