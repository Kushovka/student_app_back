import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class NotificationQueue(Base):
    __tablename__ = "notification_queue"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    behavior_record_id = Column(
        String, ForeignKey("behavior_records.id"), nullable=False, index=True
    )
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    school_id = Column(String, ForeignKey("schools.id"), nullable=False, index=True)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    channel = Column(String, nullable=False, default="email")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)

    behavior_record = relationship("BehaviorRecord")
    student = relationship("Student")
