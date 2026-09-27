from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.classroom import normalize_class_letter, validate_grade_range
from app.schemas.teacher_assignment import TeacherAssignmentCreate

from app.schemas.school import SchoolOut


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    middle_name: str
    login: str
    password: str
    school_id: str


class UserLogin(BaseModel):
    login: str
    password: str


class UserOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    middle_name: str
    login: str
    role: str
    is_blocked: bool
    school_id: str | None = None
    homeroom_grade: int | None = None
    homeroom_class_letter: str | None = None
    is_class_teacher: bool = False
    max_connected: bool = False
    school: SchoolOut | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    login: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class UserRoleUpdate(BaseModel):
    role: Literal["superadmin", "admin", "teacher", "parent"]


class UserBlockUpdate(BaseModel):
    is_blocked: bool


class UserNameUpdate(BaseModel):
    first_name: str
    last_name: str
    middle_name: str = ""


class SchoolAdminCreate(BaseModel):
    first_name: str
    last_name: str
    middle_name: str
    login: str
    password: str
    school_id: str


class SchoolUserCreate(BaseModel):
    first_name: str
    last_name: str
    middle_name: str = ""
    login: str
    password: str
    role: Literal["admin", "teacher", "parent"]
    homeroom_grade: int | None = None
    homeroom_class_letter: str | None = None
    teacher_assignments: list[TeacherAssignmentCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_homeroom(self):
        has_homeroom = self.homeroom_grade is not None or self.homeroom_class_letter is not None
        if not has_homeroom:
            if self.teacher_assignments and self.role != "teacher":
                raise ValueError("Only teachers can have teaching assignments")
            return self
        if self.homeroom_grade is None or self.homeroom_class_letter is None:
            raise ValueError("Homeroom grade and class letter must be provided together")
        if self.role != "teacher":
            raise ValueError("Only teachers can be assigned as class teachers")
        self.homeroom_grade = validate_grade_range(self.homeroom_grade)
        self.homeroom_class_letter = normalize_class_letter(self.homeroom_class_letter)
        return self


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
