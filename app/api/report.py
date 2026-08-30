from typing import Literal
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.services.report_service import (
    build_behavior_excel,
    build_behavior_docx,
    build_behavior_pdf,
    get_behavior_class_report_data,
)

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.behavior_record import BehaviorRecord
from app.models.school import School
from app.models.student import Student
from app.models.user import User
from app.schemas.report import (
    BehaviorClassReportRequest,
    BehaviorClassReportResponse,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


def require_admin(current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def require_superadmin(current_user: User) -> None:
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )


def build_school_dashboard_data(db: Session, school_id: str) -> dict:
    now = datetime.utcnow()
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    records = (
        db.query(BehaviorRecord)
        .filter(BehaviorRecord.school_id == school_id)
        .all()
    )
    severity = {"green": 0, "yellow": 0, "red": 0}
    reasons: dict[str, int] = {}
    for record in records:
        severity[record.severity] = severity.get(record.severity, 0) + 1
        for reason in record.reasons or []:
            reasons[reason] = reasons.get(reason, 0) + 1

    top_classes_rows = (
        db.query(
            Student.grade,
            Student.class_letter,
            func.count(BehaviorRecord.id).label("total"),
        )
        .join(Student, Student.id == BehaviorRecord.student_id)
        .filter(BehaviorRecord.school_id == school_id)
        .group_by(Student.grade, Student.class_letter)
        .order_by(func.count(BehaviorRecord.id).desc())
        .limit(5)
        .all()
    )

    role_counts = {
        role: (
            db.query(func.count(User.id))
            .filter(User.school_id == school_id, User.role == role)
            .scalar()
            or 0
        )
        for role in ("admin", "teacher", "parent")
    }

    return {
        "school": {
            "id": school.id,
            "name": school.name,
            "city": school.city,
        },
        "students": (
            db.query(func.count(Student.id))
            .filter(Student.school_id == school_id)
            .scalar()
            or 0
        ),
        "admins": role_counts["admin"],
        "teachers": role_counts["teacher"],
        "parents": role_counts["parent"],
        "records_total": len(records),
        "total_7_days": sum(
            1 for record in records if record.created_at >= now - timedelta(days=7)
        ),
        "total_30_days": sum(
            1 for record in records if record.created_at >= now - timedelta(days=30)
        ),
        "severity": severity,
        "top_classes": [
            {"class_name": f"{grade}{letter}", "total": total}
            for grade, letter, total in top_classes_rows
        ],
        "top_reasons": [
            {"reason": reason, "total": total}
            for reason, total in sorted(
                reasons.items(), key=lambda item: item[1], reverse=True
            )[:5]
        ],
    }


def build_export_filename(
    data: BehaviorClassReportRequest,
    extension: str,
) -> str:
    class_letter_map = str.maketrans(
        {
            "А": "A",
            "В": "B",
            "Е": "E",
            "К": "K",
            "М": "M",
            "Н": "N",
            "О": "O",
            "Р": "P",
            "С": "S",
            "Т": "T",
            "У": "Y",
            "Х": "X",
        }
    )
    class_letter = data.class_letter.strip().upper().translate(class_letter_map)
    class_name = f"{data.grade}{class_letter}"
    return (
        f"otchet_o_povedenii_{class_name}_"
        f"s_{data.date_from}_po_{data.date_to}.{extension}"
    )


@router.post("/behavior/export", response_model=BehaviorClassReportResponse)
def export_behavior_class_report(
    data: BehaviorClassReportRequest,
    format: Literal["json", "xlsx", "docx", "pdf"] = Query(default="json"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    report_data = get_behavior_class_report_data(db, current_user, data)

    if format == "xlsx":
        output = build_behavior_excel(report_data)
        filename = build_export_filename(data, "xlsx")

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    if format == "docx":
        output = build_behavior_docx(report_data)
        filename = build_export_filename(data, "docx")

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if format == "pdf":
        output = build_behavior_pdf(report_data)
        filename = build_export_filename(data, "pdf")

        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return report_data


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")

    now = datetime.utcnow()
    total_7_days = (
        db.query(func.count(BehaviorRecord.id))
        .filter(
            BehaviorRecord.school_id == current_user.school_id,
            BehaviorRecord.created_at >= now - timedelta(days=7),
        )
        .scalar()
    )
    total_30_days = (
        db.query(func.count(BehaviorRecord.id))
        .filter(
            BehaviorRecord.school_id == current_user.school_id,
            BehaviorRecord.created_at >= now - timedelta(days=30),
        )
        .scalar()
    )

    top_classes_rows = (
        db.query(
            Student.grade,
            Student.class_letter,
            func.count(BehaviorRecord.id).label("total"),
        )
        .join(Student, Student.id == BehaviorRecord.student_id)
        .filter(BehaviorRecord.school_id == current_user.school_id)
        .group_by(Student.grade, Student.class_letter)
        .order_by(func.count(BehaviorRecord.id).desc())
        .limit(5)
        .all()
    )

    records = (
        db.query(BehaviorRecord)
        .filter(BehaviorRecord.school_id == current_user.school_id)
        .all()
    )
    reasons: dict[str, int] = {}
    severity = {"green": 0, "yellow": 0, "red": 0}
    for record in records:
        severity[record.severity] = severity.get(record.severity, 0) + 1
        for reason in record.reasons or []:
            reasons[reason] = reasons.get(reason, 0) + 1

    top_reasons = [
        {"reason": reason, "total": total}
        for reason, total in sorted(reasons.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    return {
        "total_7_days": total_7_days or 0,
        "total_30_days": total_30_days or 0,
        "top_classes": [
            {"class_name": f"{grade}{letter}", "total": total}
            for grade, letter, total in top_classes_rows
        ],
        "top_reasons": top_reasons,
        "severity": severity,
    }


@router.get("/platform-dashboard")
def get_platform_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_superadmin(current_user)

    now = datetime.utcnow()
    schools = db.query(School).order_by(School.name.asc()).all()
    school_stats = []
    platform_severity = {"green": 0, "yellow": 0, "red": 0}

    total_users = db.query(func.count(User.id)).scalar() or 0
    total_students = db.query(func.count(Student.id)).scalar() or 0
    total_records = db.query(func.count(BehaviorRecord.id)).scalar() or 0
    total_7_days = (
        db.query(func.count(BehaviorRecord.id))
        .filter(BehaviorRecord.created_at >= now - timedelta(days=7))
        .scalar()
        or 0
    )
    total_30_days = (
        db.query(func.count(BehaviorRecord.id))
        .filter(BehaviorRecord.created_at >= now - timedelta(days=30))
        .scalar()
        or 0
    )

    all_records = db.query(BehaviorRecord).all()
    reasons: dict[str, int] = {}
    for record in all_records:
        platform_severity[record.severity] = platform_severity.get(record.severity, 0) + 1
        for reason in record.reasons or []:
            reasons[reason] = reasons.get(reason, 0) + 1

    for school in schools:
        school_records = (
            db.query(BehaviorRecord)
            .filter(BehaviorRecord.school_id == school.id)
            .all()
        )
        severity = {"green": 0, "yellow": 0, "red": 0}
        for record in school_records:
            severity[record.severity] = severity.get(record.severity, 0) + 1

        role_counts = {
            role: (
                db.query(func.count(User.id))
                .filter(User.school_id == school.id, User.role == role)
                .scalar()
                or 0
            )
            for role in ("admin", "teacher", "parent")
        }

        records_7_days = sum(
            1 for record in school_records if record.created_at >= now - timedelta(days=7)
        )
        records_30_days = sum(
            1 for record in school_records if record.created_at >= now - timedelta(days=30)
        )

        school_stats.append(
            {
                "school_id": school.id,
                "school_name": school.name,
                "city": school.city,
                "students": (
                    db.query(func.count(Student.id))
                    .filter(Student.school_id == school.id)
                    .scalar()
                    or 0
                ),
                "admins": role_counts["admin"],
                "teachers": role_counts["teacher"],
                "parents": role_counts["parent"],
                "records_total": len(school_records),
                "records_7_days": records_7_days,
                "records_30_days": records_30_days,
                "severity": severity,
            }
        )

    top_reasons = [
        {"reason": reason, "total": total}
        for reason, total in sorted(reasons.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    return {
        "total_schools": len(schools),
        "total_users": total_users,
        "total_students": total_students,
        "total_records": total_records,
        "total_7_days": total_7_days,
        "total_30_days": total_30_days,
        "severity": platform_severity,
        "top_reasons": top_reasons,
        "schools": sorted(
            school_stats,
            key=lambda item: (item["records_30_days"], item["records_total"]),
            reverse=True,
        ),
    }


@router.get("/platform-dashboard/schools/{school_id}")
def get_platform_school_dashboard(
    school_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_superadmin(current_user)
    return build_school_dashboard_data(db, school_id)
