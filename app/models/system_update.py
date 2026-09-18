import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String

from app.db.base import Base


class SystemUpdate(Base):
    __tablename__ = "system_updates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
