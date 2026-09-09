from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User


def notify_user(db: Session, user_id: int, *, type: str, title: str, body: str, entity: str | None = None, entity_id: int | None = None) -> Notification:
    row = Notification(user_id=user_id, type=type, title=title, body=body, entity=entity, entity_id=entity_id)
    db.add(row)
    return row


def notify_roles(db: Session, roles: set[str], **message) -> None:
    for user in db.query(User).filter(User.role.in_(roles), User.is_active == True).all():  # noqa: E712
        notify_user(db, user.id, **message)
