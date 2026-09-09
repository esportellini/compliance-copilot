from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _out(row: Notification) -> dict:
    return {"id": row.id, "type": row.type, "title": row.title, "body": row.body, "entity": row.entity, "entity_id": row.entity_id, "read_at": row.read_at, "created_at": row.created_at}


@router.get("")
def list_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Notification).filter_by(user_id=user.id)
    rows = query.order_by(Notification.created_at.desc()).limit(50).all()
    return {"unread_count": query.filter(Notification.read_at.is_(None)).count(), "items": [_out(row) for row in rows]}


@router.patch("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.query(Notification).filter_by(id=notification_id, user_id=user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    if row.read_at is None:
        row.read_at = datetime.now(timezone.utc); db.commit(); db.refresh(row)
    return _out(row)


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Notification).filter_by(user_id=user.id).filter(Notification.read_at.is_(None)).all()
    now = datetime.now(timezone.utc)
    for row in rows: row.read_at = now
    db.commit()
    return {"updated": len(rows)}
