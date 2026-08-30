import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class TeacherAssignment(Base):
    __tablename__ = "teacher_assignments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    teacher_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    school_id = Column(String, ForeignKey("schools.id"), nullable=False, index=True)
    grade = Column(Integer, nullable=False)
    class_letter = Column(String(1), nullable=False)
    subject = Column(String, nullable=False)

    teacher = relationship("User", back_populates="teacher_assignments")

    __table_args__ = (
        UniqueConstraint(
            "teacher_id",
            "grade",
            "class_letter",
            "subject",
            name="uq_teacher_assignment",
        ),
    )
