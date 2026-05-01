from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import asc
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.auth import UserBlockUpdate, UserOut, UserRoleUpdate


router = APIRouter(prefix="/users", tags=["Users"])


def require_admin(current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def get_school_user_or_404(db: Session, current_user: User, user_id: str) -> User:
    user = (
        db.query(User)
        .options(joinedload(User.school))
        .filter(User.id == user_id, User.school_id == current_user.school_id)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.get("/", response_model=list[UserOut])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not linked to a school",
        )

    users = (
        db.query(User)
        .options(joinedload(User.school))
        .filter(
            User.school_id == current_user.school_id,
            User.id != current_user.id,
        )
        .order_by(asc(User.last_name), asc(User.first_name))
        .all()
    )

    return users


@router.get("/{user_id}", response_model=UserOut)
def get_user_by_id(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not linked to a school",
        )

    return get_school_user_or_404(db, current_user, user_id)


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
