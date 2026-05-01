from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import asc
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.auth import UserOut


router = APIRouter(prefix="/users", tags=["Users"])


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
        .filter(User.school_id == current_user.school_id)
        .order_by(asc(User.last_name), asc(User.first_name))
        .all()
    )

    return users
