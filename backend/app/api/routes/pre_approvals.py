from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_compliance
from app.core.permissions import Role
from app.db.session import get_db
from app.models.pre_approval import PreApprovalComment, PreApprovalRequest
from app.models.user import User
from app.schemas.pre_approval import (
    CommentCreate, CommentOut, PreApprovalCreate,
    PreApprovalOut, PreApprovalStatusUpdate,
)
from app.services.audit import log_event

router = APIRouter(prefix="/pre-approvals", tags=["pre-approvals"])

_SEVERITY = {
    "APPROVED": "INFO",
    "APPROVED_WITH_CONDITIONS": "INFO",
    "REJECTED": "WARNING",
    "CANCELLED": "WARNING",
    "PENDING": "INFO",
    "IN_REVIEW": "INFO",
}


def _scoped(db: Session, user: User):
    q = db.query(PreApprovalRequest)
    if Role(user.role) == Role.EMPLOYEE:
        q = q.filter(PreApprovalRequest.requester_id == user.id)
    return q


@router.get("", response_model=list[PreApprovalOut])
def list_pre_approvals(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = _scoped(db, user)
    if status:
        q = q.filter(PreApprovalRequest.status == status)
    return q.order_by(PreApprovalRequest.created_at.desc()).all()


@router.get("/{req_id}", response_model=PreApprovalOut)
def get_pre_approval(
    req_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = db.get(PreApprovalRequest, req_id)
    if not r:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    if Role(user.role) == Role.EMPLOYEE and r.requester_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return r


@router.post("", response_model=PreApprovalOut, status_code=201)
def create_pre_approval(
    payload: PreApprovalCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    initial_response = None
    try:
        from app.services.copilot import CopilotInput, run_query
        inp = CopilotInput(
            user_id=user.id,
            question=(
                f"Pré-aprovação para {payload.operation_type} — "
                f"{payload.product_label or f'produto #{payload.product_id}'}"
            ),
            product_id=payload.product_id,
            amount=payload.estimated_amount,
        )
        result = run_query(inp, db)
        initial_response = result.answer
    except Exception:
        pass

    req = PreApprovalRequest(
        requester_id=user.id,
        copilot_initial_response=initial_response,
        **payload.model_dump(),
    )
    db.add(req)
    db.flush()
    log_event(
        db, "PRE_APPROVAL_CREATED",
        f"Pré-aprovação criada por {user.email}: {payload.operation_type}",
        user_id=user.id, actor_label=user.email,
        entity="pre_approval_requests", entity_id=req.id,
        meta={
            "operation_type": payload.operation_type,
            "product_label": payload.product_label,
            "estimated_amount": payload.estimated_amount,
        },
    )
    db.commit()
    db.refresh(req)
    return req


@router.patch("/{req_id}/status", response_model=PreApprovalOut)
def update_status(
    req_id: int,
    payload: PreApprovalStatusUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_compliance),
):
    r = db.get(PreApprovalRequest, req_id)
    if not r:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    if r.status in ("APPROVED", "REJECTED", "CANCELLED"):
        raise HTTPException(
            status_code=400,
            detail=f"Solicitação já encerrada com status {r.status}.",
        )

    old_status = r.status
    r.status = payload.status.value
    r.compliance_opinion = payload.compliance_opinion
    r.reviewer = actor.email
    r.decided_at = datetime.now(timezone.utc)

    log_event(
        db, "PRE_APPROVAL_DECISION",
        f"Pré-aprovação #{req_id}: {old_status} → {payload.status.value} por {actor.email}",
        user_id=actor.id, actor_label=actor.email,
        entity="pre_approval_requests", entity_id=r.id,
        severity=_SEVERITY.get(payload.status.value, "INFO"),
        meta={"old_status": old_status, "new_status": payload.status.value},
    )
    db.commit()
    db.refresh(r)
    return r


@router.post("/{req_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    req_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = db.get(PreApprovalRequest, req_id)
    if not r:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    if Role(user.role) == Role.EMPLOYEE and r.requester_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    c = PreApprovalComment(
        request_id=req_id,
        author_id=user.id,
        author_name=user.full_name,
        body=payload.body,
    )
    db.add(c)
    log_event(
        db, "PRE_APPROVAL_COMMENT",
        f"Comentário em pré-aprovação #{req_id} por {user.email}",
        user_id=user.id, actor_label=user.email,
        entity="pre_approval_requests", entity_id=req_id,
    )
    db.commit()
    db.refresh(c)
    return c
