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
    school: SchoolOut | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    email: EmailStr | None = None


class UserRoleUpdate(BaseModel):
    role: Literal["admin", "teacher"]


class UserBlockUpdate(BaseModel):
    is_blocked: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
