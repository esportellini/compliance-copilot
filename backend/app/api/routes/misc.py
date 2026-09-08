"""Miscelânea: usuários e dashboard."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.permissions import Role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.copilot import CopilotAnswer, CopilotQuery
from app.models.document import PolicyDocument
from app.models.pre_approval import PreApprovalRequest
from app.models.product import FinancialProduct
from app.models.user import User
from app.schemas.auth import UserCreate, UserOut, UserUpdate
from app.services.audit import log_event

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(User).order_by(User.full_name).all()


@users_router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    u = User(email=payload.email, full_name=payload.full_name,
             hashed_password=hash_password(payload.password),
             role=payload.role, department=payload.department)
    db.add(u); db.flush()
    log_event(db, "USER_CREATED", f"Usuário criado: {u.email}", user_id=actor.id, entity="users", entity_id=u.id)
    db.commit(); db.refresh(u)
    return u


@users_router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return u


@users_router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(u, k, v)
    log_event(db, "USER_UPDATED", f"Usuário atualizado: {u.email}", user_id=actor.id)
    db.commit(); db.refresh(u)
    return u


@users_router.patch("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: int, db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if u.id == actor.id: raise HTTPException(status_code=400, detail="Você não pode desativar sua própria conta")
    u.is_active = False
    log_event(db, "USER_DEACTIVATED", f"Usuário desativado: {u.email}", user_id=actor.id, entity="users", entity_id=u.id, severity="WARNING")
    db.commit(); db.refresh(u)
    return u


dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dashboard_router.get("")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    employee_scope = Role(user.role) == Role.EMPLOYEE
    base_q = db.query(CopilotQuery)
    if employee_scope:
        base_q = base_q.filter(CopilotQuery.user_id == user.id)
    queries_month = base_q.filter(CopilotQuery.created_at >= month_start).count()
    decision_q = (db.query(CopilotAnswer.decision, func.count())
                  .join(CopilotQuery, CopilotAnswer.query_id == CopilotQuery.id)
                  .filter(CopilotQuery.created_at >= month_start))
    pending_q = db.query(PreApprovalRequest).filter(
        PreApprovalRequest.status.in_(["PENDING", "IN_REVIEW"])
    )
    if employee_scope:
        decision_q = decision_q.filter(CopilotQuery.user_id == user.id)
        pending_q = pending_q.filter(PreApprovalRequest.requester_id == user.id)
    by_decision = {
        decision: count
        for decision, count in decision_q.group_by(CopilotAnswer.decision).all()
    }
    pending = pending_q.count()
    active_docs = db.query(PolicyDocument).filter(PolicyDocument.status == "ACTIVE").count()
    restricted = db.query(FinancialProduct).filter(FinancialProduct.status.in_(["RESTRICTED","BLOCKED"])).count()
    daily_q = (db.query(func.date(CopilotQuery.created_at).label("day"), func.count().label("count"))
               .filter(CopilotQuery.created_at >= now - timedelta(days=14)))
    recent_q = db.query(CopilotQuery).filter(CopilotQuery.created_at >= month_start)
    if employee_scope:
        daily_q = daily_q.filter(CopilotQuery.user_id == user.id)
        recent_q = recent_q.filter(CopilotQuery.user_id == user.id)
    daily = daily_q.group_by(func.date(CopilotQuery.created_at)).order_by("day").all()
    recent = recent_q.order_by(CopilotQuery.created_at.desc()).limit(5).all()
    return {
        "queries_this_month": queries_month, "by_decision": by_decision,
        "pending_approvals": pending, "active_documents": active_docs,
        "restricted_products": restricted,
        "queries_by_day": [{"date": str(r.day), "count": r.count} for r in daily],
        "recent_queries": [{"id": q.id, "question": q.question[:80],
                            "decision": q.answer.decision if q.answer else None,
                            "created_at": str(q.created_at)} for q in recent],
    }
