from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.school import School
from app.models.user import User
from app.schemas.school import SchoolCreate, SchoolOut


router = APIRouter(prefix="/schools", tags=["Schools"])


def require_superadmin(current_user: User) -> None:
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )


@router.get("/", response_model=list[SchoolOut])
def get_schools(db: Session = Depends(get_db)):
    return db.query(School).order_by(asc(School.name)).all()


@router.post("/", response_model=SchoolOut)
def create_school(
    data: SchoolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_superadmin(current_user)
    school = School(name=data.name.strip(), city=(data.city or "").strip() or None)
    db.add(school)
    db.commit()
    db.refresh(school)
    return school


@router.patch("/{school_id}", response_model=SchoolOut)
def update_school(
    school_id: str,
    data: SchoolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_superadmin(current_user)
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    school.name = data.name.strip()
    school.city = (data.city or "").strip() or None
    db.commit()
    db.refresh(school)
    return school


@router.delete("/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_school(
    school_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_superadmin(current_user)
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    db.delete(school)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
