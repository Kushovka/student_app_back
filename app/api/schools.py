from fastapi import APIRouter, Depends
from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.school import School
from app.schemas.school import SchoolOut


router = APIRouter(prefix="/schools", tags=["Schools"])


@router.get("/", response_model=list[SchoolOut])
def get_schools(db: Session = Depends(get_db)):
    return db.query(School).order_by(asc(School.name)).all()
