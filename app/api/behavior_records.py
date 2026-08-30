import logging
import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.behavior_record import BehaviorRecord
from app.models.notification_queue import NotificationQueue
from app.models.parent_student import ParentStudent
from app.models.student import Student
from app.models.teacher_assignment import TeacherAssignment
from app.models.user import User
from app.schemas.behavior_record import BehaviorCreate, BehaviorOut
from app.services.behavior_services import send_digest_email
from app.services.max_services import send_behavior_max_message

router = APIRouter(prefix="/behavior", tags=["Behavior"])
logger = logging.getLogger(__name__)
upload_dir = Path("uploads/behavior_records")


def require_admin(current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def parent_can_access_student(db: Session, parent: User, student_id: str) -> bool:
    return (
        db.query(ParentStudent.id)
        .join(Student, Student.id == ParentStudent.student_id)
        .filter(
            ParentStudent.parent_id == parent.id,
            ParentStudent.student_id == student_id,
            Student.school_id == parent.school_id,
        )
        .first()
        is not None
    )


def get_parent_emails(db: Session, student_id: str) -> list[str]:
    rows = (
        db.query(User.email)
        .join(ParentStudent, ParentStudent.parent_id == User.id)
        .filter(
            ParentStudent.student_id == student_id,
            User.role == "parent",
            User.is_blocked.is_(False),
        )
        .all()
    )
    return [email for (email,) in rows if email]


def get_parent_max_user_ids(db: Session, student_id: str) -> list[str]:
    rows = (
        db.query(User.max_user_id)
        .join(ParentStudent, ParentStudent.parent_id == User.id)
        .filter(
            ParentStudent.student_id == student_id,
            User.role == "parent",
            User.is_blocked.is_(False),
            User.max_user_id.isnot(None),
        )
        .all()
    )
    return [max_user_id for (max_user_id,) in rows if max_user_id]


def teacher_can_access_class(db: Session, teacher: User, student: Student) -> bool:
    return (
        db.query(TeacherAssignment.id)
        .filter(
            TeacherAssignment.teacher_id == teacher.id,
            TeacherAssignment.school_id == teacher.school_id,
            TeacherAssignment.grade == student.grade,
            TeacherAssignment.class_letter == student.class_letter,
        )
        .first()
        is not None
    )


def teacher_can_create_subject(
    db: Session,
    teacher: User,
    student: Student,
    subject: str,
) -> bool:
    return (
        db.query(TeacherAssignment.id)
        .filter(
            TeacherAssignment.teacher_id == teacher.id,
            TeacherAssignment.school_id == teacher.school_id,
            TeacherAssignment.grade == student.grade,
            TeacherAssignment.class_letter == student.class_letter,
            TeacherAssignment.subject == subject,
        )
        .first()
        is not None
    )


@router.post("/{student_id}", response_model=BehaviorOut)
async def add_behavior(
    student_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    if current_user.role == "parent":
        raise HTTPException(status_code=403, detail="Parents cannot create behavior records")

    student = (
        db.query(Student)
        .filter(Student.id == student_id, Student.school_id == current_user.school_id)
        .first()
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    content_type = request.headers.get("content-type", "")
    photo_url = None
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        raw_reasons = form.get("reasons") or "[]"
        try:
            reasons = json.loads(str(raw_reasons))
        except json.JSONDecodeError:
            reasons = [part.strip() for part in str(raw_reasons).split(",") if part.strip()]

        payload = BehaviorCreate(
            subject=str(form.get("subject") or ""),
            reasons=reasons,
            comment=str(form.get("comment") or "") or None,
        )
        photo = form.get("photo")
        if hasattr(photo, "filename") and getattr(photo, "filename", None):
            suffix = Path(photo.filename).suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
                raise HTTPException(status_code=400, detail="Only jpg, png and webp files are supported")
            upload_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid.uuid4()}{suffix}"
            target = upload_dir / filename
            target.write_bytes(await photo.read())
            photo_url = f"/uploads/behavior_records/{filename}"
    else:
        payload = BehaviorCreate.model_validate(await request.json())
        photo_url = payload.photo_url

    if current_user.role == "teacher" and not teacher_can_create_subject(
        db,
        current_user,
        student,
        payload.subject,
    ):
        raise HTTPException(
            status_code=403,
            detail="Teacher is not assigned to this class and subject",
        )

    record = BehaviorRecord(
        student_id=student_id,
        school_id=current_user.school_id,
        severity="yellow",
        subject=payload.subject,
        reasons=payload.reasons,
        comment=payload.comment,
        photo_url=photo_url,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    queue_item = NotificationQueue(
        behavior_record_id=record.id,
        student_id=student.id,
        school_id=current_user.school_id,
        severity="yellow",
        status="pending",
        channel="email",
    )
    db.add(queue_item)
    db.commit()
    db.refresh(queue_item)

    try:
        send_behavior_max_message(
            student,
            current_user,
            record,
            get_parent_max_user_ids(db, student.id),
        )
    except Exception:
        logger.exception("Failed to send MAX message for record %s", record.id)

    return record


@router.post("/digests/send")
def send_pending_digests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    require_admin(current_user)

    queue_items = (
        db.query(NotificationQueue)
        .filter(
            NotificationQueue.school_id == current_user.school_id,
            NotificationQueue.status == "pending",
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
            send_digest_email(student, records, get_parent_emails(db, student.id))
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
    if current_user.role == "parent" and not parent_can_access_student(db, current_user, student.id):
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "teacher" and not teacher_can_access_class(db, current_user, student):
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
