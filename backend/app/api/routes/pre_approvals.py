from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.permissions import Role
from app.db.session import get_db
from app.models.copilot import CopilotQuery
from app.models.pre_approval import PreApprovalComment, PreApprovalRequest
from app.models.product import FinancialProduct
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
_WORKFLOW_WRITER = require_roles(Role.ADMIN, Role.COMPLIANCE, Role.EMPLOYEE)
_ALLOWED_TRANSITIONS = {
    "PENDING": {"IN_REVIEW", "REJECTED", "CANCELLED"},
    "IN_REVIEW": {
        "APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED", "CANCELLED",
    },
    "APPROVED": set(),
    "APPROVED_WITH_CONDITIONS": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
}
_OPINION_REQUIRED = {"APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED"}


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
    user: User = Depends(_WORKFLOW_WRITER),
):
    source_query = None
    product = None
    if payload.source_query_id is not None:
        source_query = db.get(CopilotQuery, payload.source_query_id)
        if not source_query:
            raise HTTPException(status_code=404, detail="Consulta do Copilot não encontrada")
        if source_query.user_id != user.id:
            raise HTTPException(status_code=403, detail="A consulta pertence a outro usuário")
        if not source_query.answer:
            raise HTTPException(status_code=409, detail="A consulta ainda não possui análise persistida")
        if source_query.product_id is not None:
            product = db.get(FinancialProduct, source_query.product_id)
        initial_response = source_query.answer.answer
        initial_decision = source_query.answer.decision
        product_id = source_query.product_id
        estimated_amount = source_query.amount
        justification = payload.justification or source_query.objective
    else:
        product_id = payload.product_id
        if product_id is not None:
            product = db.get(FinancialProduct, product_id)
            if not product:
                raise HTTPException(status_code=404, detail="Produto não encontrado")
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
        initial_decision = result.decision
        estimated_amount = payload.estimated_amount
        justification = payload.justification

    product_label = payload.product_label
    if product:
        product_label = product.name
        if product.identifier:
            product_label = f"{product.name} ({product.identifier})"

    req = PreApprovalRequest(
        requester_id=user.id,
        source_query_id=source_query.id if source_query else None,
        product_id=product_id,
        product_label=product_label,
        operation_type=payload.operation_type,
        estimated_amount=estimated_amount,
        intended_date=payload.intended_date,
        justification=justification,
        copilot_initial_response=initial_response,
        copilot_initial_decision=initial_decision,
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
            "product_label": product_label,
            "estimated_amount": estimated_amount,
            "source_query_id": source_query.id if source_query else None,
            "copilot_initial_decision": initial_decision,
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
    actor: User = Depends(get_current_user),
):
    r = db.get(PreApprovalRequest, req_id)
    if not r:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    actor_role = Role(actor.role)
    target = payload.status.value
    if actor_role == Role.AUDITOR:
        raise HTTPException(status_code=403, detail="Auditor possui acesso somente leitura")
    if actor_role == Role.EMPLOYEE:
        if not (
            r.requester_id == actor.id
            and r.status == "PENDING"
            and target == "CANCELLED"
        ):
            raise HTTPException(status_code=403, detail="Acesso negado")
    elif actor_role not in (Role.ADMIN, Role.COMPLIANCE):
        raise HTTPException(status_code=403, detail="Acesso negado")

    if target not in _ALLOWED_TRANSITIONS.get(r.status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Transição inválida: {r.status} → {target}.",
        )
    opinion = payload.compliance_opinion.strip() if payload.compliance_opinion else None
    if target in _OPINION_REQUIRED and not opinion:
        raise HTTPException(status_code=400, detail="Parecer de compliance obrigatório")

    old_status = r.status
    r.status = target
    r.compliance_opinion = opinion
    r.reviewer = actor.email
    now = datetime.now(timezone.utc)
    if target == "IN_REVIEW":
        r.review_started_at = now
        event_type = "PRE_APPROVAL_REVIEW_STARTED"
    elif target in _OPINION_REQUIRED:
        r.decided_at = now
        event_type = "PRE_APPROVAL_DECISION"
    else:
        event_type = "PRE_APPROVAL_CANCELLED"

    log_event(
        db, event_type,
        f"Pré-aprovação #{req_id}: {old_status} → {target} por {actor.email}",
        user_id=actor.id, actor_label=actor.email,
        entity="pre_approval_requests", entity_id=r.id,
        severity=_SEVERITY.get(target, "INFO"),
        meta={
            "old_status": old_status,
            "new_status": target,
            "source_query_id": r.source_query_id,
        },
    )
    db.commit()
    db.refresh(r)
    return r


@router.post("/{req_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    req_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_WORKFLOW_WRITER),
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
