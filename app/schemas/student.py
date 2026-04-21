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


class StudentOut(StudentBase):
    id: str
    school_id: str

    class Config:
        from_attributes = True
