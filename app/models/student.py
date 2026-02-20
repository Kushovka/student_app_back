import uuid

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    grade = Column(Integer, nullable=False)
    class_letter = Column(String(1), nullable=False)

    behavior_records = relationship(
        "BehaviorRecord", backref="student", cascade="all, delete"
    )
