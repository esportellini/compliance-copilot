from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_compliance
from app.db.session import get_db
from app.models.product import FinancialProduct
from app.models.rule import ComplianceRule
from app.models.user import User
from app.schemas.enums import Decision, RiskLevel
from app.schemas.rule import RuleCreate, RuleEvaluateRequest, RuleOut, RuleUpdate
from app.services.audit import get_setting, log_event
from app.services.rules_engine import EvaluationContext, RuleSpec, evaluate

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ComplianceRule).order_by(ComplianceRule.priority).all()


@router.post("", response_model=RuleOut, status_code=201)
def create_rule(payload: RuleCreate, db: Session = Depends(get_db), actor: User = Depends(require_compliance)):
    r = ComplianceRule(**payload.model_dump())
    db.add(r)
    db.flush()
    log_event(db, "RULE_CREATED", f"Regra criada: {r.name}", user_id=actor.id, entity="compliance_rules", entity_id=r.id)
    db.commit()
    db.refresh(r)
    return r


@router.patch("/{rule_id}", response_model=RuleOut)
def update_rule(rule_id: int, payload: RuleUpdate, db: Session = Depends(get_db), actor: User = Depends(require_compliance)):
    r = db.get(ComplianceRule, rule_id)
    if not r:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(r, k, v)
    log_event(db, "RULE_UPDATED", f"Regra atualizada: {r.name}", user_id=actor.id, entity="compliance_rules", entity_id=r.id)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db), _: User = Depends(require_compliance)):
    r = db.get(ComplianceRule, rule_id)
    if not r:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    db.delete(r)
    db.commit()


@router.post("/evaluate")
def evaluate_rule(payload: RuleEvaluateRequest, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    threshold = float(get_setting(db, "human_review_threshold") or "100000")
    product_status = "ALLOWED"
    if payload.product_id:
        p = db.get(FinancialProduct, payload.product_id)
        if p:
            product_status = p.status
            if not payload.product_type:
                payload.product_type = p.product_type
    from app.models.restricted import RestrictedListItem
    on_restricted = False
    if payload.product_type:
        on_restricted = bool(
            db.query(RestrictedListItem)
            .filter(RestrictedListItem.active == True, RestrictedListItem.identifier.ilike(payload.product_type))  # noqa: E712
            .first()
        )
    rules_db = db.query(ComplianceRule).filter(ComplianceRule.is_active == True).all()  # noqa: E712
    rules = [RuleSpec(name=r.name, decision=Decision(r.decision), risk=RiskLevel(r.risk),
                      priority=r.priority, product_type=r.product_type, condition=r.condition or {})
             for r in rules_db]
    ctx = EvaluationContext(
        product_type=payload.product_type,
        product_status=product_status,
        on_restricted_list=on_restricted,
        amount=payload.amount,
        human_review_threshold=threshold,
    )
    result = evaluate(ctx, rules)
    return {"decision": result.decision, "reason": result.reason,
            "matched_rules": result.matched_rules, "risk_level": result.risk_level,
            "requires_human_review": result.requires_human_review}
