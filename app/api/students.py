from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentOut

router = APIRouter(prefix="/student", tags=["Students"])


class NotificationRequests(BaseModel):
    subject: str
    message: str


@router.get("/", response_model=list[StudentOut])
def get_students(
    grade: Optional[int] = None,
    class_letter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Student)

    if grade is not None:
        query = query.filter(Student.grade == grade)

    if class_letter is not None:
        query = query.filter(Student.class_letter == class_letter)

    query = query.order_by(asc(Student.last_name))

    return query.all()


@router.get("/{student_id}", response_model=StudentOut)
def get_student_by_id(student_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student is noy found")

    return student


@router.post("/", response_model=StudentOut)
def create_students(data: StudentCreate, db: Session = Depends(get_db)):
    student = Student(
        first_name=data.first_name,
        last_name=data.last_name,
        middle_name=data.middle_name,
        email=data.email,
        grade=data.grade,
        class_letter=data.class_letter.strip().upper(),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    db.delete(student)
    db.commit()
