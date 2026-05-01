from typing import Optional
from sqlalchemy import and_, or_

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.student import Student
from app.models.user import User
from app.schemas.student import StudentCreate, StudentListResponse, StudentOut

router = APIRouter(prefix="/student", tags=["Students"])


class NotificationRequests(BaseModel):
    subject: str
    message: str


@router.get("/", response_model=StudentListResponse)
def get_students(
    grade: Optional[int] = None,
    class_letter: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")

    query = db.query(Student).filter(Student.school_id == current_user.school_id)

    if grade is not None:
        query = query.filter(Student.grade == grade)

    if class_letter is not None:
        query = query.filter(Student.class_letter == class_letter)

    if search and search.strip():
        search_terms = search.strip().split()
        query = query.filter(
            and_(
                *[
                    or_(
                        Student.first_name.ilike(f"{term}%"),
                        Student.last_name.ilike(f"{term}%"),
                        Student.middle_name.ilike(f"{term}%"),
                    )
                    for term in search_terms
                ]
            )
        )

    total = query.count()
    offset = (page - 1) * limit
    pages = (total + limit - 1) // limit if total > 0 else 0

    items = (
        query.order_by(asc(Student.last_name), asc(Student.first_name))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
    }


@router.get("/{student_id}", response_model=StudentOut)
def get_student_by_id(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")

    student = (
        db.query(Student)
        .filter(Student.id == student_id, Student.school_id == current_user.school_id)
        .first()
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return student


@router.post("/", response_model=StudentOut)
def create_students(
    data: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")

    student = Student(
        first_name=data.first_name,
        last_name=data.last_name,
        middle_name=data.middle_name,
        email=data.email,
        grade=data.grade,
        class_letter=data.class_letter.strip().upper(),
        school_id=current_user.school_id,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=204)
def delete_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")

    student = (
        db.query(Student)
        .filter(Student.id == student_id, Student.school_id == current_user.school_id)
        .first()
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    db.delete(student)
    db.commit()
