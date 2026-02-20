from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.behavior_record import BehaviorRecord
from app.models.student import Student
from app.schemas.behavior_record import BehaviorCreate
from app.services.behavior_services import send_behavior_email

router = APIRouter(prefix="/behavior", tags=["Behavior"])


@router.post("/{student_id}")
def add_behavior(
    student_id: str, payload: BehaviorCreate, db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    record = BehaviorRecord(
        student_id=student_id,
        subject=payload.subject,
        reasons=payload.reasons,
        comment=payload.comment,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    send_behavior_email(student, payload.subject, payload.reasons, payload.comment)

    return record


@router.get("/{student_id}")
def get_behavior(student_id: str, db: Session = Depends(get_db)):
    records = (
        db.query(BehaviorRecord)
        .filter(BehaviorRecord.student_id == student_id)
        .order_by(BehaviorRecord.created_at.desc())
        .all()
    )

    return records
