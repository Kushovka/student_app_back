import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from app.db.base import Base


class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    school_id = Column(String, ForeignKey("schools.id"), nullable=False, index=True)
    grade = Column(Integer, nullable=False)
    class_letter = Column(String(1), nullable=False)

    __table_args__ = (
        UniqueConstraint("school_id", "grade", "class_letter", name="uq_classroom_school_grade_letter"),
    )
