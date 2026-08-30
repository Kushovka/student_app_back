from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import asc
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.security import hash_password
from app.db.deps import get_db
from app.models.school import School
from app.models.teacher_assignment import TeacherAssignment
from app.models.user import User
from app.schemas.auth import (
    SchoolAdminCreate,
    SchoolUserCreate,
    UserBlockUpdate,
    UserOut,
    UserRoleUpdate,
)
from app.schemas.teacher_assignment import (
    TeacherAssignmentCreate,
    TeacherAssignmentOut,
)


router = APIRouter(prefix="/users", tags=["Users"])


def require_admin(current_user: User) -> None:
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def get_school_user_or_404(db: Session, current_user: User, user_id: str) -> User:
    user = (
        db.query(User)
        .options(joinedload(User.school))
        .filter(User.id == user_id)
        .first()
    )
    if user and current_user.role != "superadmin" and user.school_id != current_user.school_id:
        user = None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def normalize_assignment(data: TeacherAssignmentCreate) -> tuple[int, str, str]:
    class_letter = data.class_letter
    subject = data.subject.strip()
    if not class_letter or not subject:
        raise HTTPException(status_code=400, detail="Class letter and subject are required")
    return data.grade, class_letter, subject


@router.get("/", response_model=list[UserOut])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "superadmin" and not current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not linked to a school",
        )
    require_admin(current_user)

    query = db.query(User).options(joinedload(User.school))
    if current_user.role != "superadmin":
        query = query.filter(User.school_id == current_user.school_id)
    users = query.order_by(asc(User.last_name), asc(User.first_name)).all()

    return users


@router.get("/me/assignments", response_model=list[TeacherAssignmentOut])
def get_my_teacher_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        return []
    if not current_user.school_id:
        raise HTTPException(status_code=403, detail="User is not linked to a school")

    return (
        db.query(TeacherAssignment)
        .filter(
            TeacherAssignment.teacher_id == current_user.id,
            TeacherAssignment.school_id == current_user.school_id,
        )
        .order_by(
            asc(TeacherAssignment.grade),
            asc(TeacherAssignment.class_letter),
            asc(TeacherAssignment.subject),
        )
        .all()
    )


@router.get("/{user_id}", response_model=UserOut)
def get_user_by_id(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "superadmin" and not current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not linked to a school",
        )
    require_admin(current_user)

    return get_school_user_or_404(db, current_user, user_id)


@router.get("/{teacher_id}/assignments", response_model=list[TeacherAssignmentOut])
def get_teacher_assignments(
    teacher_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    teacher = get_school_user_or_404(db, current_user, teacher_id)
    if teacher.role != "teacher":
        raise HTTPException(status_code=400, detail="User is not a teacher")

    return (
        db.query(TeacherAssignment)
        .filter(
            TeacherAssignment.teacher_id == teacher.id,
            TeacherAssignment.school_id == teacher.school_id,
        )
        .order_by(
            asc(TeacherAssignment.grade),
            asc(TeacherAssignment.class_letter),
            asc(TeacherAssignment.subject),
        )
        .all()
    )


@router.post(
    "/{teacher_id}/assignments",
    response_model=TeacherAssignmentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_teacher_assignment(
    teacher_id: str,
    data: TeacherAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" or not current_user.school_id:
        raise HTTPException(status_code=403, detail="School admin access required")

    teacher = get_school_user_or_404(db, current_user, teacher_id)
    if teacher.role != "teacher" or teacher.school_id != current_user.school_id:
        raise HTTPException(status_code=400, detail="User is not a teacher in this school")

    grade, class_letter, subject = normalize_assignment(data)
    existing = (
        db.query(TeacherAssignment)
        .filter(
            TeacherAssignment.teacher_id == teacher.id,
            TeacherAssignment.grade == grade,
            TeacherAssignment.class_letter == class_letter,
            TeacherAssignment.subject == subject,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Assignment already exists")

    assignment = TeacherAssignment(
        teacher_id=teacher.id,
        school_id=current_user.school_id,
        grade=grade,
        class_letter=class_letter,
        subject=subject,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/{teacher_id}/assignments/{assignment_id}", status_code=204)
def delete_teacher_assignment(
    teacher_id: str,
    assignment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" or not current_user.school_id:
        raise HTTPException(status_code=403, detail="School admin access required")

    teacher = get_school_user_or_404(db, current_user, teacher_id)
    assignment = (
        db.query(TeacherAssignment)
        .filter(
            TeacherAssignment.id == assignment_id,
            TeacherAssignment.teacher_id == teacher.id,
            TeacherAssignment.school_id == current_user.school_id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/school-admin", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_school_admin(
    data: SchoolAdminCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")

    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    school = db.query(School).filter(School.id == data.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    user = User(
        first_name=data.first_name,
        last_name=data.last_name,
        middle_name=data.middle_name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role="admin",
        is_blocked=False,
        school_id=data.school_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return get_school_user_or_404(db, current_user, user.id)


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_school_user(
    data: SchoolUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" or not current_user.school_id:
        raise HTTPException(status_code=403, detail="School admin access required")

    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    user = User(
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        middle_name=data.middle_name.strip(),
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
        is_blocked=False,
        school_id=current_user.school_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return get_school_user_or_404(db, current_user, user.id)


@router.patch("/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: str,
    data: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role",
        )

    user = get_school_user_or_404(db, current_user, user_id)
    if current_user.role != "superadmin" and data.role == "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can assign superadmin role")
    user.role = data.role
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/block", response_model=UserOut)
def update_user_block_status(
    user_id: str,
    data: UserBlockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot block or unblock yourself",
        )

    user = get_school_user_or_404(db, current_user, user_id)
    user.is_blocked = data.is_blocked
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete yourself",
        )

    user = get_school_user_or_404(db, current_user, user_id)
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
