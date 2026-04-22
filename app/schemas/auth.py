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
    school_id: str | None = None
    school: SchoolOut | None = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
