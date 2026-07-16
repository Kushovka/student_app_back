from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class BehaviorCreate(BaseModel):
    severity: Literal["green", "yellow", "red"] = "yellow"
    subject: str
    reasons: List[str]
    comment: Optional[str] = Field(default=None, max_length=150)


class BehaviorOut(BehaviorCreate):
    id: str
    student_id: str
    school_id: str
    created_at: datetime

    class Config:
        from_attributes = True
