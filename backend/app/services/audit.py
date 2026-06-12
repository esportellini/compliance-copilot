from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.setting import SystemSetting


def log_event(
    db: Session,
    event_type: str,
    message: str,
    *,
    user_id: int | None = None,
    actor_label: str | None = None,
    entity: str | None = None,
    entity_id: int | None = None,
    severity: str = "INFO",
    meta: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        event_type=event_type,
        message=message,
        user_id=user_id,
        actor_label=actor_label,
        entity=entity,
        entity_id=entity_id,
        severity=severity,
        meta=meta or {},
    )
    db.add(entry)
    return entry


def get_setting(db: Session, key: str, default: str | None = None) -> str | None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return row.value if row else default


def set_setting(db: Session, key: str, value: str, description: str | None = None) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value, description=description))
