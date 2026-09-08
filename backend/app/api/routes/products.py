from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_compliance
from app.db.session import get_db
from app.models.copilot import CopilotAnswer, CopilotQuery
from app.models.product import FinancialProduct
from app.models.user import User
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services.audit import log_event

router = APIRouter(prefix="/products", tags=["products"])


def _flush_product(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe produto com identifier equivalente.",
        ) from exc


@router.get("", response_model=list[ProductOut])
def list_products(
    q: str | None = Query(default=None, description="busca por nome ou identificador"),
    product_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    risk: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(FinancialProduct)
    if q:
        like = f"%{q}%"
        query = query.filter(
            FinancialProduct.name.ilike(like) | FinancialProduct.identifier.ilike(like)
        )
    if product_type:
        query = query.filter(FinancialProduct.product_type == product_type)
    if status:
        query = query.filter(FinancialProduct.status == status)
    if risk:
        query = query.filter(FinancialProduct.risk == risk)
    return query.order_by(FinancialProduct.name).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    p = db.get(FinancialProduct, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return p


@router.get("/{product_id}/queries")
def get_product_queries(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Histórico de consultas do Copilot referenciando este produto."""
    if not db.get(FinancialProduct, product_id):
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    rows = (
        db.query(CopilotQuery)
        .filter(CopilotQuery.product_id == product_id)
        .order_by(CopilotQuery.created_at.desc())
        .limit(20)
        .all()
    )
    result = []
    for row in rows:
        ans = row.answer
        result.append(
            {
                "id": row.id,
                "question": row.question,
                "decision": ans.decision if ans else None,
                "risk_level": ans.risk_level if ans else None,
                "created_at": str(row.created_at),
            }
        )
    return result


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_compliance),
):
    p = FinancialProduct(**payload.model_dump())
    db.add(p)
    _flush_product(db)
    log_event(
        db, "PRODUCT_CREATED", f"Produto criado: {p.name}",
        user_id=actor.id, actor_label=actor.email,
        entity="financial_products", entity_id=p.id,
        meta={"product_type": p.product_type, "status": p.status},
    )
    db.commit()
    db.refresh(p)
    return p


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_compliance),
):
    p = db.get(FinancialProduct, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    old_status = p.status
    changes = payload.model_dump(exclude_none=True)
    for k, v in changes.items():
        setattr(p, k, v)
    _flush_product(db)

    # auditoria extra quando status muda para restrito/bloqueado
    new_status = changes.get("status", old_status)
    if new_status != old_status:
        severity = "WARNING" if new_status in ("RESTRICTED", "BLOCKED") else "INFO"
        log_event(
            db, "PRODUCT_STATUS_CHANGED",
            f"Status do produto '{p.name}' alterado: {old_status} → {new_status}",
            user_id=actor.id, actor_label=actor.email,
            entity="financial_products", entity_id=p.id,
            severity=severity,
            meta={"old_status": old_status, "new_status": new_status},
        )
    else:
        log_event(
            db, "PRODUCT_UPDATED", f"Produto atualizado: {p.name}",
            user_id=actor.id, actor_label=actor.email,
            entity="financial_products", entity_id=p.id,
        )
    db.commit()
    db.refresh(p)
    return p


@router.patch("/{product_id}/restrict", response_model=ProductOut)
def restrict_product(
    product_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_compliance),
):
    p = db.get(FinancialProduct, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if p.status == "BLOCKED":
        raise HTTPException(status_code=400, detail="Produto já está bloqueado")
    old = p.status
    p.status = "RESTRICTED"
    log_event(
        db, "PRODUCT_RESTRICTED", f"Produto marcado como RESTRICTED: {p.name}",
        user_id=actor.id, actor_label=actor.email,
        entity="financial_products", entity_id=p.id,
        severity="WARNING", meta={"old_status": old},
    )
    db.commit()
    db.refresh(p)
    return p


@router.patch("/{product_id}/block", response_model=ProductOut)
def block_product(
    product_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_compliance),
):
    p = db.get(FinancialProduct, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    old = p.status
    p.status = "BLOCKED"
    log_event(
        db, "PRODUCT_BLOCKED", f"Produto marcado como BLOCKED: {p.name}",
        user_id=actor.id, actor_label=actor.email,
        entity="financial_products", entity_id=p.id,
        severity="WARNING", meta={"old_status": old},
    )
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_compliance),
):
    p = db.get(FinancialProduct, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    log_event(
        db, "PRODUCT_DELETED", f"Produto removido: {p.name}",
        user_id=actor.id, actor_label=actor.email,
        entity="financial_products", entity_id=p.id,
        severity="WARNING",
    )
    db.delete(p)
    db.commit()
