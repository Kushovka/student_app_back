import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import relationship as orm_relationship

from app.db.base import Base


class ParentStudent(Base):
    __tablename__ = "parent_students"
    __table_args__ = (
        UniqueConstraint("parent_id", "student_id", name="uq_parent_student"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    parent_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(
        String, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    relationship = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    parent = orm_relationship("User", back_populates="student_links")
    student = orm_relationship("Student", back_populates="parent_links")
