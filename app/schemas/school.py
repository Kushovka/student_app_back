from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SchoolOut(BaseModel):
    id: str
    name: str
    city: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
