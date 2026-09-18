import csv
import re
import subprocess
import tempfile
from io import BytesIO, StringIO
from pathlib import Path
from typing import Optional

from docx import Document
from openpyxl import Workbook, load_workbook
from sqlalchemy import and_, false, or_

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import asc
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.parent_student import ParentStudent
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.teacher_assignment import TeacherAssignment
from app.models.user import User
from app.schemas.auth import UserOut
from app.schemas.classroom import MAX_GRADE, MIN_GRADE, normalize_class_letter, validate_grade_range
from app.schemas.student import (
    ClassOptionsResponse,
    ClassroomCreate,
    ParentStudentCreate,
    ParentStudentOut,
    StudentCreate,
    StudentListResponse,
    StudentOut,
    StudentUpdate,
    HomeroomTeacherOut,
)

router = APIRouter(prefix="/student", tags=["Students"])

CLASS_HEADING_RE = re.compile(
    r"\b(?P<grade>\d{1,2})\s*[«\"“”']?\s*(?P<letter>[А-ЯЁ])\s*[»\"“”']?\s+класс[а-яё]*\b",
    re.IGNORECASE,
)
STUDENT_LINE_RE = re.compile(
    r"^\s*(?:\d+[.)]\s*)?(?P<last>[А-ЯЁ][А-ЯЁа-яё'-]*)\s+"
    r"(?P<first>[А-ЯЁ][А-ЯЁа-яё'-]*)\s+"
    r"(?P<middle>[А-ЯЁ][А-ЯЁа-яё'-]*)\s*$"
)


class NotificationRequests(BaseModel):
    subject: str
    message: str


def require_admin(current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def require_parent_manager(current_user: User) -> None:
    if current_user.role != "admin" and not current_user.is_class_teacher:
        raise HTTPException(status_code=403, detail="Parent management access required")


def build_class_suffix(grade: int | None, class_letter: str | None) -> str:
    if not grade or not class_letter:
        return ""
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
    letter = class_letter.strip().upper().translate(class_letter_map)
    return f"_{grade}{letter}"


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


def teacher_class_clauses(db: Session, teacher: User):
    assignments = (
        db.query(TeacherAssignment.grade, TeacherAssignment.class_letter)
        .filter(
            TeacherAssignment.teacher_id == teacher.id,
            TeacherAssignment.school_id == teacher.school_id,
        )
        .distinct()
        .all()
    )
    if teacher.is_class_teacher:
        assignments.append((teacher.homeroom_grade, teacher.homeroom_class_letter))
    if not assignments:
        return [false()]
    return [
        and_(Student.grade == grade, Student.class_letter == class_letter)
        for grade, class_letter in assignments
    ]


def teacher_can_access_student(db: Session, teacher: User, student: Student) -> bool:
    if class_teacher_can_access_student(teacher, student):
        return True
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


def class_teacher_can_access_student(class_teacher: User, student: Student) -> bool:
    return (
        class_teacher.is_class_teacher
        and class_teacher.homeroom_grade == student.grade
        and class_teacher.homeroom_class_letter == student.class_letter
    )


def get_homeroom_teacher(db: Session, student: Student) -> User | None:
    return (
        db.query(User)
        .filter(
            User.school_id == student.school_id,
            User.role == "teacher",
            User.is_blocked.is_(False),
            User.homeroom_grade == student.grade,
            User.homeroom_class_letter == student.class_letter,
        )
        .order_by(User.last_name, User.first_name)
        .first()
    )


def class_exists(db: Session, school_id: str, grade: int, class_letter: str) -> bool:
    return (
        db.query(Classroom.id)
        .filter(
            Classroom.school_id == school_id,
            Classroom.grade == grade,
            Classroom.class_letter == class_letter,
        )
        .first()
        is not None
    )


def extract_word_text(filename: str, raw: bytes) -> str:
    if filename.endswith(".docx"):
        document = Document(BytesIO(raw))
        lines = [paragraph.text for paragraph in document.paragraphs]
        for table in document.tables:
            lines.extend(" ".join(cell.text for cell in row.cells) for row in table.rows)
        return "\n".join(lines)

    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = Path(temp_dir) / "students.doc"
        source_path.write_bytes(raw)
        try:
            result = subprocess.run(
                ["antiword", "-w", "0", str(source_path)],
                capture_output=True,
                check=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise HTTPException(
                status_code=400,
                detail="Не удалось прочитать Word-файл. Сохраните его как DOCX или XLSX и повторите импорт.",
            ) from exc
    return result.stdout


def parse_word_students(text: str, grade: int, class_letter: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    active_class = False
    has_class_headings = False

    for raw_line in text.splitlines():
        line = " ".join(raw_line.replace("\ufeff", "").replace("|", " ").split())
        heading = CLASS_HEADING_RE.search(line)
        if heading:
            has_class_headings = True
            active_class = (
                int(heading.group("grade")) == grade
                and normalize_class_letter(heading.group("letter")) == class_letter
            )
            continue

        if line.lower().startswith(("директор", "классный руководитель")):
            active_class = False
            continue

        if has_class_headings and not active_class:
            continue

        student = STUDENT_LINE_RE.fullmatch(line)
        if student:
            rows.append(
                {
                    "last_name": student.group("last"),
                    "first_name": student.group("first"),
                    "middle_name": student.group("middle"),
                }
            )

    return rows


def parse_word_class_lists(text: str, grade: int) -> dict[str, list[dict[str, str]]]:
    class_lists: dict[str, list[dict[str, str]]] = {}
    active_letter: str | None = None

    for raw_line in text.splitlines():
        line = " ".join(raw_line.replace("\ufeff", "").replace("|", " ").split())
        heading = CLASS_HEADING_RE.search(line)
        if heading:
            heading_grade = int(heading.group("grade"))
            active_letter = (
                normalize_class_letter(heading.group("letter"))
                if heading_grade == grade
                else None
            )
            if active_letter:
                class_lists.setdefault(active_letter, [])
            continue

        if line.lower().startswith(("директор", "классный руководитель")):
            active_letter = None
            continue

        if not active_letter:
            continue

        student = STUDENT_LINE_RE.fullmatch(line)
        if student:
            class_lists[active_letter].append(
                {
                    "last_name": student.group("last"),
                    "first_name": student.group("first"),
                    "middle_name": student.group("middle"),
                }
            )

    return {letter: students for letter, students in class_lists.items() if students}


@router.post("/classes", response_model=ClassroomCreate, status_code=201)
def create_classroom(
    data: ClassroomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    require_admin(current_user)
    if class_exists(db, current_user.school_id, data.grade, data.class_letter):
        raise HTTPException(status_code=409, detail="Class already exists")

    classroom = Classroom(
        school_id=current_user.school_id,
        grade=data.grade,
        class_letter=data.class_letter,
    )
    db.add(classroom)
    db.commit()
    return {"grade": classroom.grade, "class_letter": classroom.class_letter}


@router.delete("/classes/{grade}/{class_letter}", status_code=204)
def delete_classroom(
    grade: int,
    class_letter: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    require_admin(current_user)
    try:
        normalized_grade = validate_grade_range(grade)
        normalized_letter = normalize_class_letter(class_letter)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid grade or class letter") from None

    classroom = (
        db.query(Classroom)
        .filter(
            Classroom.school_id == current_user.school_id,
            Classroom.grade == normalized_grade,
            Classroom.class_letter == normalized_letter,
        )
        .first()
    )
    if not classroom:
        raise HTTPException(status_code=404, detail="Class not found")

    has_students = (
        db.query(Student.id)
        .filter(
            Student.school_id == current_user.school_id,
            Student.grade == normalized_grade,
            Student.class_letter == normalized_letter,
        )
        .first()
        is not None
    )
    if has_students:
        raise HTTPException(
            status_code=409,
            detail="Remove or move all students before deleting this class",
        )

    db.delete(classroom)
    db.commit()


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

    query = db.query(Student).filter(
        Student.school_id == current_user.school_id,
        Student.grade.between(MIN_GRADE, MAX_GRADE),
    )
    normalized_class_letter = None
    if class_letter is not None:
        try:
            normalized_class_letter = normalize_class_letter(class_letter)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid class letter") from None

    if current_user.role == "parent":
        query = query.join(ParentStudent).filter(ParentStudent.parent_id == current_user.id)
    elif current_user.role == "teacher":
        query = query.filter(or_(*teacher_class_clauses(db, current_user)))

    if grade is not None:
        try:
            grade = validate_grade_range(grade)
        except ValueError:
            raise HTTPException(status_code=400, detail="Grade must be between 5 and 9") from None
        query = query.filter(Student.grade == grade)

    if normalized_class_letter is not None:
        query = query.filter(Student.class_letter == normalized_class_letter)

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


@router.get("/class-options", response_model=ClassOptionsResponse)
def get_class_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")

    query = (
        db.query(Classroom.grade, Classroom.class_letter)
        .filter(
            Classroom.school_id == current_user.school_id,
            Classroom.grade.between(MIN_GRADE, MAX_GRADE),
        )
        .distinct()
    )

    if current_user.role == "parent":
        query = (
            query.join(
                Student,
                and_(
                    Student.school_id == Classroom.school_id,
                    Student.grade == Classroom.grade,
                    Student.class_letter == Classroom.class_letter,
                ),
            )
            .join(ParentStudent)
            .filter(ParentStudent.parent_id == current_user.id)
        )
    elif current_user.role == "teacher":
        assignments = (
            db.query(TeacherAssignment.grade, TeacherAssignment.class_letter)
            .filter(
                TeacherAssignment.teacher_id == current_user.id,
                TeacherAssignment.school_id == current_user.school_id,
            )
            .distinct()
            .all()
        )
        accessible_classes = {
            (assignment_grade, assignment_letter)
            for assignment_grade, assignment_letter in assignments
        }
        if current_user.is_class_teacher:
            accessible_classes.add(
                (current_user.homeroom_grade, current_user.homeroom_class_letter)
            )

        if not accessible_classes:
            query = query.filter(false())
        else:
            query = query.filter(
                or_(
                    *[
                        and_(Classroom.grade == grade, Classroom.class_letter == class_letter)
                        for grade, class_letter in accessible_classes
                    ]
                )
            )

    rows = query.order_by(asc(Classroom.grade), asc(Classroom.class_letter)).all()
    classes = [
        {"grade": grade, "class_letter": class_letter}
        for grade, class_letter in rows
    ]

    return {
        "grades": sorted({grade for grade, _ in rows}),
        "letters": sorted({class_letter for _, class_letter in rows}),
        "classes": classes,
    }


@router.get("/export")
def export_students(
    grade: Optional[int] = None,
    class_letter: Optional[str] = None,
    format: str = Query(default="xlsx", pattern="^(csv|xlsx)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    require_admin(current_user)

    query = db.query(Student).filter(
        Student.school_id == current_user.school_id,
        Student.grade.between(MIN_GRADE, MAX_GRADE),
    )
    if grade is not None:
        try:
            grade = validate_grade_range(grade)
        except ValueError:
            raise HTTPException(status_code=400, detail="Grade must be between 5 and 9") from None
        query = query.filter(Student.grade == grade)
    if class_letter is not None:
        try:
            class_letter = normalize_class_letter(class_letter)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid class letter") from None
        query = query.filter(Student.class_letter == class_letter)

    students = query.order_by(asc(Student.grade), asc(Student.class_letter), asc(Student.last_name)).all()
    filename_class = build_class_suffix(grade, class_letter)

    headers = ["last_name", "first_name", "middle_name", "grade", "class_letter"]
    rows = [
        [
            student.last_name,
            student.first_name,
            student.middle_name,
            student.grade,
            student.class_letter,
        ]
        for student in students
    ]

    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)
        return StreamingResponse(
            iter([output.getvalue().encode("utf-8-sig")]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="students{filename_class}.csv"'
            },
        )

    output = BytesIO()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ученики"
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    for column, width in {"A": 20, "B": 18, "C": 22, "D": 10, "E": 14}.items():
        sheet.column_dimensions[column].width = width
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="students{filename_class}.xlsx"'
        },
    )


@router.post("/import")
def import_students(
    file: UploadFile = File(...),
    grade: Optional[int] = None,
    class_letter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    require_admin(current_user)

    raw = file.file.read()
    name = (file.filename or "").lower()
    rows: list[dict[str, str]] = []

    target_grade = None
    target_letter = None
    if grade is not None or class_letter is not None:
        if grade is None or class_letter is None:
            raise HTTPException(status_code=400, detail="Grade and class_letter must be provided together")
        try:
            target_grade = validate_grade_range(grade)
            target_letter = normalize_class_letter(class_letter)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid grade or class_letter") from None
        if not class_exists(db, current_user.school_id, target_grade, target_letter):
            raise HTTPException(status_code=404, detail="Class not found")

    if name.endswith(".csv"):
        text = raw.decode("utf-8-sig")
        rows = list(csv.DictReader(StringIO(text)))
    elif name.endswith(".xlsx"):
        workbook = load_workbook(BytesIO(raw), read_only=True, data_only=True)
        sheet = workbook.active
        values = list(sheet.iter_rows(values_only=True))
        if values:
            headers = [str(value).strip() for value in values[0]]
            for row in values[1:]:
                rows.append(
                    {
                        headers[index]: "" if value is None else str(value).strip()
                        for index, value in enumerate(row)
                        if index < len(headers)
                    }
                )
    elif name.endswith((".doc", ".docx")):
        if target_grade is None or target_letter is None:
            raise HTTPException(
                status_code=400,
                detail="Для Word-файла выберите страницу нужного класса перед импортом",
            )
        rows = parse_word_students(
            extract_word_text(name, raw), target_grade, target_letter
        )
        if not rows:
            raise HTTPException(
                status_code=400,
                detail="В файле не найден нумерованный список учеников выбранного класса",
            )
    else:
        raise HTTPException(status_code=400, detail="Поддерживаются файлы CSV, XLSX, DOC и DOCX")

    required = {"last_name", "first_name", "middle_name"}
    if target_grade is None:
        required.update({"grade", "class_letter"})
    created = 0
    skipped = 0
    errors: list[str] = []

    for index, row in enumerate(rows, start=2):
        normalized = {str(key).strip(): value for key, value in row.items() if key is not None}
        if not required.issubset(normalized.keys()):
            skipped += 1
            errors.append(f"Row {index}: missing required columns")
            continue

        try:
            row_grade = target_grade or validate_grade_range(int(str(normalized["grade"]).strip()))
            row_class_letter = target_letter or normalize_class_letter(str(normalized["class_letter"]))
        except ValueError:
            skipped += 1
            errors.append(f"Row {index}: invalid grade or class_letter")
            continue

        if not class_exists(db, current_user.school_id, row_grade, row_class_letter):
            skipped += 1
            errors.append(f"Row {index}: class does not exist")
            continue

        student = Student(
            first_name=str(normalized["first_name"]).strip(),
            last_name=str(normalized["last_name"]).strip(),
            middle_name=str(normalized["middle_name"]).strip(),
            grade=row_grade,
            class_letter=row_class_letter,
            school_id=current_user.school_id,
        )
        db.add(student)
        created += 1

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors[:20]}


@router.post("/import-class-lists")
def import_word_class_lists(
    file: UploadFile = File(...),
    grade: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    require_admin(current_user)
    try:
        target_grade = validate_grade_range(grade)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid grade") from None

    name = (file.filename or "").lower()
    if not name.endswith((".doc", ".docx")):
        raise HTTPException(status_code=400, detail="Для импорта списков нужен Word-файл DOC или DOCX")

    class_lists = parse_word_class_lists(
        extract_word_text(name, file.file.read()), target_grade
    )
    if not class_lists:
        raise HTTPException(
            status_code=400,
            detail="В файле не найдены нумерованные списки выбранной параллели",
        )

    existing_classes = {
        class_letter
        for (class_letter,) in db.query(Classroom.class_letter)
        .filter(
            Classroom.school_id == current_user.school_id,
            Classroom.grade == target_grade,
        )
        .all()
    }
    created_classes: list[str] = []
    for class_letter in sorted(class_lists):
        if class_letter not in existing_classes:
            db.add(
                Classroom(
                    school_id=current_user.school_id,
                    grade=target_grade,
                    class_letter=class_letter,
                )
            )
            created_classes.append(class_letter)

    existing_students = {
        (student.class_letter, student.last_name, student.first_name, student.middle_name)
        for student in db.query(Student)
        .filter(
            Student.school_id == current_user.school_id,
            Student.grade == target_grade,
            Student.class_letter.in_(class_lists),
        )
        .all()
    }
    created_students = 0
    skipped_students = 0
    seen_students: set[tuple[str, str, str, str]] = set()
    for class_letter, students in class_lists.items():
        for student in students:
            student_key = (
                class_letter,
                student["last_name"],
                student["first_name"],
                student["middle_name"],
            )
            if student_key in existing_students or student_key in seen_students:
                skipped_students += 1
                continue
            db.add(
                Student(
                    school_id=current_user.school_id,
                    grade=target_grade,
                    class_letter=class_letter,
                    **student,
                )
            )
            seen_students.add(student_key)
            created_students += 1

    db.commit()
    return {
        "created_classes": created_classes,
        "created_students": created_students,
        "skipped_students": skipped_students,
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
        .filter(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
            Student.grade.between(MIN_GRADE, MAX_GRADE),
        )
        .first()
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "parent" and not parent_can_access_student(db, current_user, student.id):
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "teacher" and not teacher_can_access_student(db, current_user, student):
        raise HTTPException(status_code=404, detail="Student not found")

    return student


@router.get("/{student_id}/class-teacher", response_model=HomeroomTeacherOut | None)
def get_student_class_teacher(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")

    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
            Student.grade.between(MIN_GRADE, MAX_GRADE),
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "parent" and not parent_can_access_student(db, current_user, student.id):
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "teacher" and not teacher_can_access_student(db, current_user, student):
        raise HTTPException(status_code=404, detail="Student not found")

    return get_homeroom_teacher(db, student)


@router.get("/{student_id}/parents", response_model=list[ParentStudentOut])
def get_student_parents(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    if current_user.role == "teacher" and not current_user.is_class_teacher:
        raise HTTPException(status_code=403, detail="Teachers cannot access parent links")

    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
            Student.grade.between(MIN_GRADE, MAX_GRADE),
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "parent" and not parent_can_access_student(db, current_user, student.id):
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "teacher" and not class_teacher_can_access_student(current_user, student):
        raise HTTPException(status_code=404, detail="Student not found")

    return (
        db.query(ParentStudent)
        .options(joinedload(ParentStudent.parent))
        .filter(ParentStudent.student_id == student.id)
        .join(User, User.id == ParentStudent.parent_id)
        .order_by(asc(User.last_name), asc(User.first_name))
        .all()
    )


@router.get("/{student_id}/parents/available", response_model=list[UserOut])
def get_available_parents(
    student_id: str,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    require_parent_manager(current_user)

    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
            Student.grade.between(MIN_GRADE, MAX_GRADE),
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "teacher" and not class_teacher_can_access_student(current_user, student):
        raise HTTPException(status_code=404, detail="Student not found")

    linked_parent_ids = (
        db.query(ParentStudent.parent_id)
        .filter(ParentStudent.student_id == student.id)
        .subquery()
    )
    query = (
        db.query(User)
        .filter(
            User.school_id == current_user.school_id,
            User.role == "parent",
            User.id.notin_(linked_parent_ids),
        )
    )
    if search and search.strip():
        search_terms = search.strip().split()
        query = query.filter(
            and_(
                *[
                    or_(
                        User.first_name.ilike(f"{term}%"),
                        User.last_name.ilike(f"{term}%"),
                        User.middle_name.ilike(f"{term}%"),
                        User.login.ilike(f"{term}%"),
                    )
                    for term in search_terms
                ]
            )
        )

    return query.order_by(asc(User.last_name), asc(User.first_name)).limit(20).all()


@router.post("/{student_id}/parents", response_model=ParentStudentOut, status_code=201)
def attach_parent_to_student(
    student_id: str,
    data: ParentStudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    require_parent_manager(current_user)

    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
            Student.grade.between(MIN_GRADE, MAX_GRADE),
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "teacher" and not class_teacher_can_access_student(current_user, student):
        raise HTTPException(status_code=404, detail="Student not found")

    parent = (
        db.query(User)
        .filter(
            User.id == data.parent_id,
            User.school_id == current_user.school_id,
            User.role == "parent",
        )
        .first()
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    existing = (
        db.query(ParentStudent)
        .filter(
            ParentStudent.parent_id == parent.id,
            ParentStudent.student_id == student.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Parent is already linked")

    link = ParentStudent(
        parent_id=parent.id,
        student_id=student.id,
        relationship=data.relationship.strip() if data.relationship else None,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return (
        db.query(ParentStudent)
        .options(joinedload(ParentStudent.parent))
        .filter(ParentStudent.id == link.id)
        .first()
    )


@router.delete("/{student_id}/parents/{parent_id}", status_code=204)
def detach_parent_from_student(
    student_id: str,
    parent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    require_parent_manager(current_user)

    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
            Student.grade.between(MIN_GRADE, MAX_GRADE),
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    link = (
        db.query(ParentStudent)
        .join(User, User.id == ParentStudent.parent_id)
        .filter(
            ParentStudent.student_id == student.id,
            ParentStudent.parent_id == parent_id,
            User.school_id == current_user.school_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Parent link not found")

    db.delete(link)
    db.commit()


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: str,
    data: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    require_admin(current_user)

    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
            Student.grade.between(MIN_GRADE, MAX_GRADE),
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    next_grade = data.grade if data.grade is not None else student.grade
    next_class_letter = data.class_letter if data.class_letter is not None else student.class_letter
    if not class_exists(db, current_user.school_id, next_grade, next_class_letter):
        raise HTTPException(status_code=404, detail="Class not found")

    if data.first_name is not None:
        student.first_name = data.first_name
    if data.last_name is not None:
        student.last_name = data.last_name
    if data.middle_name is not None:
        student.middle_name = data.middle_name
    if data.grade is not None:
        student.grade = data.grade
    if data.class_letter is not None:
        student.class_letter = data.class_letter

    db.commit()
    db.refresh(student)
    return student


@router.post("/", response_model=StudentOut)
def create_students(
    data: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")
    require_admin(current_user)

    if not class_exists(db, current_user.school_id, data.grade, data.class_letter):
        raise HTTPException(status_code=404, detail="Class not found")

    student = Student(
        first_name=data.first_name,
        last_name=data.last_name,
        middle_name=data.middle_name,
        grade=data.grade,
        class_letter=data.class_letter,
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
    require_admin(current_user)

    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
            Student.grade.between(MIN_GRADE, MAX_GRADE),
        )
        .first()
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    db.delete(student)
    db.commit()
