"""Auditoria e exportação CSV."""
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_global_view
from app.core.permissions import Role
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.common import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["audit"])

_VISIBLE_EVENTS = {
    Role.COMPLIANCE: lambda q: q.filter(AuditLog.event_type != "UNAUTHORIZED_ACCESS"),
    Role.AUDITOR:    lambda q: q.filter(AuditLog.event_type != "UNAUTHORIZED_ACCESS"),
    Role.ADMIN:      lambda q: q,
}


@router.get("", response_model=list[AuditLogOut])
def list_audit(
    event_type: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    severity: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(require_global_view),
):
    role = Role(user.role)
    q = db.query(AuditLog)

    # filtra eventos por papel
    if role in _VISIBLE_EVENTS:
        q = _VISIBLE_EVENTS[role](q)

    if event_type:
        q = q.filter(AuditLog.event_type.ilike(f"%{event_type}%"))
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if severity:
        q = q.filter(AuditLog.severity == severity)
    if date_from:
        try:
            q = q.filter(AuditLog.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(AuditLog.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))
        except ValueError:
            pass

    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()


@router.get("/export/csv")
def export_csv(
    event_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_global_view),
):
    role = Role(user.role)
    q = db.query(AuditLog)
    if role in _VISIBLE_EVENTS:
        q = _VISIBLE_EVENTS[role](q)
    if event_type:
        q = q.filter(AuditLog.event_type.ilike(f"%{event_type}%"))
    if severity:
        q = q.filter(AuditLog.severity == severity)
    if date_from:
        try:
            q = q.filter(AuditLog.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(AuditLog.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))
        except ValueError:
            pass

    rows = q.order_by(AuditLog.created_at.desc()).limit(5000).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "data", "evento", "ator", "entidade", "entidade_id", "severidade", "mensagem"])
    for r in rows:
        writer.writerow([
            r.id,
            r.created_at.isoformat() if r.created_at else "",
            r.event_type,
            r.actor_label or "",
            r.entity or "",
            r.entity_id or "",
            r.severity,
            r.message,
        ])

    buf.seek(0)
    filename = f"auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
