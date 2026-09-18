from datetime import datetime

from pydantic import BaseModel


class SystemUpdateOut(BaseModel):
    id: str
    title: str
    description: str
    published_at: datetime

    class Config:
        from_attributes = True


class SystemUpdatesResponse(BaseModel):
    items: list[SystemUpdateOut]
    unread_count: int
