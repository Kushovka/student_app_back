import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.behavior_record import BehaviorRecord
from app.models.notification_queue import NotificationQueue
from app.models.student import Student
from app.models.user import User
from app.schemas.behavior_record import BehaviorCreate, BehaviorOut
from app.services.behavior_services import send_behavior_email, send_digest_email

router = APIRouter(prefix="/behavior", tags=["Behavior"])
logger = logging.getLogger(__name__)


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
        severity=payload.severity,
        subject=payload.subject,
        reasons=payload.reasons,
        comment=payload.comment,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    queue_item = NotificationQueue(
        behavior_record_id=record.id,
        student_id=student.id,
        school_id=current_user.school_id,
        severity=record.severity,
        status="pending",
        channel="email",
    )
    db.add(queue_item)
    db.commit()
    db.refresh(queue_item)

    if payload.severity == "red":
        try:
            send_behavior_email(
                student,
                current_user,
                payload.subject,
                payload.reasons,
                payload.comment,
            )
            queue_item.status = "sent"
            queue_item.sent_at = datetime.utcnow()
            db.commit()
        except Exception:
            queue_item.status = "failed"
            db.commit()
            logger.exception("Failed to send behavior email for record %s", record.id)

    return record


@router.post("/digests/send")
def send_pending_digests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")

    queue_items = (
        db.query(NotificationQueue)
        .filter(
            NotificationQueue.school_id == current_user.school_id,
            NotificationQueue.status == "pending",
            NotificationQueue.severity.in_(["green", "yellow"]),
        )
        .all()
    )

    by_student: dict[str, list[NotificationQueue]] = {}
    for item in queue_items:
        by_student.setdefault(item.student_id, []).append(item)

    sent_students = 0
    sent_records = 0
    for student_id, items in by_student.items():
        student = (
            db.query(Student)
            .filter(Student.id == student_id, Student.school_id == current_user.school_id)
            .first()
        )
        if not student:
            continue

        records = [item.behavior_record for item in items if item.behavior_record]
        try:
            send_digest_email(student, records)
            now = datetime.utcnow()
            for item in items:
                item.status = "sent"
                item.sent_at = now
            sent_students += 1
            sent_records += len(items)
        except Exception:
            for item in items:
                item.status = "failed"
            logger.exception("Failed to send digest for student %s", student_id)

    db.commit()

    return {
        "queued": len(queue_items),
        "sent_students": sent_students,
        "sent_records": sent_records,
    }


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
