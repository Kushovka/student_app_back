from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserCreate


def get_user_by_login(db: Session, login: str) -> User | None:
    normalized_login = login.strip().lower()
    return db.query(User).filter(func.lower(User.login) == normalized_login).first()


def create_user(db: Session, data: UserCreate) -> User:
    user = User(
        first_name=data.first_name,
        last_name=data.last_name,
        middle_name=data.middle_name,
        login=data.login.strip().lower(),
        hashed_password=hash_password(data.password),
        role="teacher",
        school_id=data.school_id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, login: str, password: str) -> User | None:
    user = get_user_by_login(db, login)

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
