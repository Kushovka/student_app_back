import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String

from app.db.base import Base


class BehaviorRecord(Base):
    __tablename__ = "behavior_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    subject = Column(String, nullable=False)
    reasons = Column(JSON, nullable=False)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
