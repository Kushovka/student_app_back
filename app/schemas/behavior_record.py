from typing import List, Optional

from pydantic import BaseModel


class BehaviorCreate(BaseModel):
    subject: str
    reasons: List[str]
    comment: Optional[str] = None
