from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.system_update import SystemUpdate
from app.models.user import User
from app.schemas.system_update import SystemUpdatesResponse


router = APIRouter(prefix="/system-updates", tags=["System updates"])


def visible_updates_query(db: Session, current_user: User):
    return db.query(SystemUpdate).filter(
        SystemUpdate.published_at >= current_user.created_at,
    )


@router.get("", response_model=SystemUpdatesResponse)
def get_system_updates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = visible_updates_query(db, current_user)
    updates = query.order_by(desc(SystemUpdate.published_at)).limit(20).all()

    unread_query = visible_updates_query(db, current_user)
    if current_user.system_updates_seen_at is not None:
        unread_query = unread_query.filter(
            SystemUpdate.published_at > current_user.system_updates_seen_at,
        )

    return SystemUpdatesResponse(items=updates, unread_count=unread_query.count())


@router.patch("/read", response_model=SystemUpdatesResponse)
def mark_system_updates_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updates = (
        visible_updates_query(db, current_user)
        .order_by(desc(SystemUpdate.published_at))
        .limit(20)
        .all()
    )

    if updates:
        current_user.system_updates_seen_at = updates[0].published_at
        db.commit()

    return SystemUpdatesResponse(items=updates, unread_count=0)
