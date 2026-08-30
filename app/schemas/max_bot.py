from pydantic import BaseModel


class MaxLinkCodeOut(BaseModel):
    code: str
    bot_username: str | None = None
    connected: bool


class MaxWebhookOut(BaseModel):
    ok: bool
    detail: str
