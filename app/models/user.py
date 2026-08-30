import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="teacher")
    is_blocked = Column(Boolean, nullable=False, default=False)
    school_id = Column(String, ForeignKey("schools.id"), nullable=True)
    max_user_id = Column(String, unique=True, nullable=True)
    max_chat_id = Column(String, nullable=True)
    max_link_code = Column(String, unique=True, nullable=True)

    school = relationship("School", back_populates="users")
    student_links = relationship(
        "ParentStudent",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    teacher_assignments = relationship(
        "TeacherAssignment",
        back_populates="teacher",
        cascade="all, delete-orphan",
    )

    @property
    def max_connected(self) -> bool:
        return bool(self.max_user_id)
