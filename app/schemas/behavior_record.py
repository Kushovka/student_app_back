from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class BehaviorCreate(BaseModel):
    subject: str
    reasons: List[str]
    comment: Optional[str] = None


class BehaviorOut(BehaviorCreate):
    id: str
    student_id: str
    school_id: str
    created_at: datetime

    class Config:
        from_attributes = True
