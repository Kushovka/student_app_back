from typing import Literal

from pydantic import BaseModel, EmailStr

from app.schemas.school import SchoolOut


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    middle_name: str
    email: EmailStr
    password: str
    school_id: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    middle_name: str
    email: EmailStr
    role: str
    is_blocked: bool
    school_id: str | None = None
    max_connected: bool = False
    school: SchoolOut | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    email: EmailStr | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class UserRoleUpdate(BaseModel):
    role: Literal["superadmin", "admin", "teacher", "parent"]


class UserBlockUpdate(BaseModel):
    is_blocked: bool


class SchoolAdminCreate(BaseModel):
    first_name: str
    last_name: str
    middle_name: str
    email: EmailStr
    password: str
    school_id: str


class SchoolUserCreate(BaseModel):
    first_name: str
    last_name: str
    middle_name: str = ""
    email: EmailStr
    password: str
    role: Literal["admin", "teacher", "parent"]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
