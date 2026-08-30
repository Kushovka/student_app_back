from pydantic import BaseModel, field_validator

from app.schemas.auth import UserOut
from app.schemas.classroom import normalize_class_letter, validate_grade_range


class StudentBase(BaseModel):
    first_name: str
    last_name: str
    middle_name: str
    grade: int
    class_letter: str
    email: str = ""

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, value: int) -> int:
        return validate_grade_range(value)

    @field_validator("class_letter")
    @classmethod
    def validate_class_letter(cls, value: str) -> str:
        return normalize_class_letter(value)


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    grade: int | None = None
    class_letter: str | None = None
    email: str | None = None

    @field_validator("grade")
    @classmethod
    def validate_optional_grade(cls, value: int | None) -> int | None:
        if value is None:
            return value
        return validate_grade_range(value)

    @field_validator("class_letter")
    @classmethod
    def validate_optional_class_letter(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return normalize_class_letter(value)


class StudentOut(StudentBase):
    id: str
    school_id: str

    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    items: list[StudentOut]
    total: int
    page: int
    limit: int
    pages: int


class ClassOption(BaseModel):
    grade: int
    class_letter: str


class ClassOptionsResponse(BaseModel):
    grades: list[int]
    letters: list[str]
    classes: list[ClassOption]


class ParentStudentCreate(BaseModel):
    parent_id: str
    relationship: str | None = None


class ParentStudentOut(BaseModel):
    id: str
    parent_id: str
    student_id: str
    relationship: str | None = None
    parent: UserOut

    class Config:
        from_attributes = True
