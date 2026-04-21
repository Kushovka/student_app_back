from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.behavior_record import BehaviorRecord
from app.models.student import Student
from app.models.user import User
from app.schemas.behavior_record import BehaviorCreate, BehaviorOut
from app.services.behavior_services import send_behavior_email

router = APIRouter(prefix="/behavior", tags=["Behavior"])


@router.post("/{student_id}", response_model=BehaviorOut)
def add_behavior(
    student_id: str,
    payload: BehaviorCreate,
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

    record = BehaviorRecord(
        student_id=student_id,
        school_id=current_user.school_id,
        subject=payload.subject,
        reasons=payload.reasons,
        comment=payload.comment,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    send_behavior_email(
        student,
        current_user,
        payload.subject,
        payload.reasons,
        payload.comment,
    )

    return record


@router.get("/{student_id}", response_model=list[BehaviorOut])
def get_behavior(
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

    records = (
        db.query(BehaviorRecord)
        .filter(
            BehaviorRecord.student_id == student_id,
            BehaviorRecord.school_id == current_user.school_id,
        )
        .order_by(BehaviorRecord.created_at.desc())
        .all()
    )

    return records
