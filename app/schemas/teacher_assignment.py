from pydantic import BaseModel, field_validator

from app.schemas.classroom import normalize_class_letter, validate_grade_range


class TeacherAssignmentCreate(BaseModel):
    grade: int
    class_letter: str
    subject: str

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, value: int) -> int:
        return validate_grade_range(value)

    @field_validator("class_letter")
    @classmethod
    def validate_class_letter(cls, value: str) -> str:
        return normalize_class_letter(value)


class TeacherAssignmentOut(BaseModel):
    id: str
    teacher_id: str
    school_id: str
    grade: int
    class_letter: str
    subject: str

    class Config:
        from_attributes = True
