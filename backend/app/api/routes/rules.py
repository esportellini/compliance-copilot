import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_compliance
from app.core.identifiers import normalize_identifier, normalized_identifier_expression
from app.db.session import get_db
from app.models.product import FinancialProduct
from app.models.restricted import RestrictedListItem
from app.models.rule import ComplianceRule
from app.models.user import User
from app.schemas.enums import Decision, RiskLevel
from app.schemas.rule import RuleCreate, RuleEvaluateRequest, RuleOut, RuleUpdate
from app.services.audit import log_event
from app.services.rules_engine import EvaluationContext, RuleSpec, evaluate

router = APIRouter(prefix="/rules", tags=["rules"])


def _utc(value: datetime | None) -> datetime:
    value = value or datetime.now(timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "rule"


def _ensure_dates(start: datetime, end: datetime | None) -> None:
    if end is not None and _utc(end) <= _utc(start):
        raise HTTPException(status_code=422, detail="effective_to deve ser posterior a effective_from")


@router.get("", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ComplianceRule).order_by(ComplianceRule.rule_key, ComplianceRule.version.desc()).all()


@router.get("/by-key/{rule_key}", response_model=list[RuleOut])
def rule_versions(rule_key: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(ComplianceRule).filter_by(rule_key=rule_key).order_by(ComplianceRule.version.desc()).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    return rows


@router.post("", response_model=RuleOut, status_code=201)
def create_rule(payload: RuleCreate, db: Session = Depends(get_db), actor: User = Depends(require_compliance)):
    data = payload.model_dump(exclude_none=True)
    rule_key = data.pop("rule_key", None) or _key(payload.name)
    version = (db.query(func.max(ComplianceRule.version)).filter_by(rule_key=rule_key).scalar() or 0) + 1
    status = data.get("status", "ACTIVE")
    start = _utc(data.get("effective_from"))
    _ensure_dates(start, data.get("effective_to"))
    if status == "ACTIVE" and db.query(ComplianceRule).filter_by(rule_key=rule_key, status="ACTIVE").first():
        raise HTTPException(status_code=409, detail="Já existe versão ACTIVE para esta regra")
    data.update(rule_key=rule_key, version=version, effective_from=start, created_by=actor.id)
    data["is_active"] = status == "ACTIVE"
    row = ComplianceRule(**data)
    db.add(row)
    db.flush()
    log_event(db, "RULE_CREATED", f"Regra criada: {row.rule_key} v{row.version}", user_id=actor.id, actor_label=actor.email, entity="compliance_rules", entity_id=row.id)
    db.commit(); db.refresh(row)
    return row


@router.post("/{rule_id}/activate", response_model=RuleOut)
def activate_rule(rule_id: int, db: Session = Depends(get_db), actor: User = Depends(require_compliance)):
    row = db.get(ComplianceRule, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    if row.status == "ARCHIVED":
        raise HTTPException(status_code=409, detail="Versão arquivada é imutável")
    start = _utc(row.effective_from)
    _ensure_dates(start, row.effective_to)
    active = db.query(ComplianceRule).filter(ComplianceRule.rule_key == row.rule_key, ComplianceRule.status == "ACTIVE", ComplianceRule.id != row.id).all()
    for previous in active:
        previous.status, previous.is_active = "ARCHIVED", False
        if previous.effective_to is None or _utc(previous.effective_to) > start:
            previous.effective_to = start
    row.status, row.is_active = "ACTIVE", True
    log_event(db, "RULE_ACTIVATED", f"Regra ativada: {row.rule_key} v{row.version}", user_id=actor.id, actor_label=actor.email, entity="compliance_rules", entity_id=row.id)
    db.commit(); db.refresh(row)
    return row


@router.patch("/{rule_id}", response_model=RuleOut)
def update_rule(rule_id: int, payload: RuleUpdate, db: Session = Depends(get_db), actor: User = Depends(require_compliance)):
    row = db.get(ComplianceRule, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    changes = payload.model_dump(exclude_none=True)
    if row.status == "DRAFT":
        for key, value in changes.items(): setattr(row, key, value)
        row.is_active = row.status == "ACTIVE"
        _ensure_dates(_utc(row.effective_from), row.effective_to)
        result = row
    else:
        excluded = {"id", "created_at", "updated_at"}
        data = {column.name: getattr(row, column.name) for column in ComplianceRule.__table__.columns if column.name not in excluded}
        data.update(changes)
        next_version = (db.query(func.max(ComplianceRule.version)).filter_by(rule_key=row.rule_key).scalar() or 0) + 1
        data.update(version=next_version, created_by=actor.id)
        data["effective_from"] = _utc(changes.get("effective_from"))
        data["effective_to"] = changes.get("effective_to")
        data["status"] = "ACTIVE" if row.status == "ACTIVE" else "DRAFT"
        data["is_active"] = data["status"] == "ACTIVE"
        _ensure_dates(data["effective_from"], data["effective_to"])
        if row.status == "ACTIVE":
            row.status, row.is_active, row.effective_to = "ARCHIVED", False, data["effective_from"]
        result = ComplianceRule(**data)
        db.add(result)
    db.flush()
    log_event(db, "RULE_VERSION_CREATED" if result.id != row.id else "RULE_DRAFT_UPDATED", f"Regra atualizada: {result.rule_key} v{result.version}", user_id=actor.id, actor_label=actor.email, entity="compliance_rules", entity_id=result.id)
    db.commit(); db.refresh(result)
    return result


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db), _: User = Depends(require_compliance)):
    row = db.get(ComplianceRule, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    if row.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Versões publicadas não podem ser removidas")
    db.delete(row); db.commit()


@router.post("/evaluate")
def evaluate_rule(payload: RuleEvaluateRequest, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    product_status = "ALLOWED"
    product = db.get(FinancialProduct, payload.product_id) if payload.product_id is not None else None
    if payload.product_id is not None and product is None:
        return {"decision": Decision.INCONCLUSIVE, "reason": f"Produto informado não encontrado: id={payload.product_id}.", "matched_rules": [], "risk_level": RiskLevel.MEDIUM, "requires_human_review": True}
    if product: product_status, payload.product_type = product.status, product.product_type
    on_restricted = bool(product and product.identifier and db.query(RestrictedListItem).filter(RestrictedListItem.active == True, normalized_identifier_expression(RestrictedListItem.identifier) == normalize_identifier(product.identifier)).first())  # noqa: E712
    now = datetime.now(timezone.utc)
    rows = db.query(ComplianceRule).filter(ComplianceRule.status == "ACTIVE", ComplianceRule.is_active == True, ComplianceRule.effective_from <= now, or_(ComplianceRule.effective_to.is_(None), ComplianceRule.effective_to > now)).all()  # noqa: E712
    rules = [RuleSpec(name=r.name, decision=Decision(r.decision), risk=RiskLevel(r.risk), priority=r.priority, product_type=r.product_type, condition=r.condition or {}) for r in rows]
    result = evaluate(EvaluationContext(product_type=payload.product_type, product_status=product_status, on_restricted_list=on_restricted, amount=payload.amount), rules)
    return {"decision": result.decision, "reason": result.reason, "matched_rules": result.matched_rules, "risk_level": result.risk_level, "requires_human_review": result.requires_human_review}
