from pydantic import BaseModel


class StudentBase(BaseModel):
    first_name: str
    last_name: str
    middle_name: str
    grade: int
    class_letter: str
    email: str


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    grade: int | None = None
    class_letter: str | None = None
    email: str | None = None


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
