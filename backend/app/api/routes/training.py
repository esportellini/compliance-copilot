"""Módulo de treinamento e onboarding."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin, require_roles
from app.core.permissions import Role
from app.db.session import get_db
from app.models.training import TrainingItem, UserTrainingAcknowledgement
from app.models.user import User
from app.schemas.common import TrainingAcknowledge, TrainingItemOut
from app.services.audit import log_event

router = APIRouter(prefix="/training", tags=["training"])
_TRAINING_WRITER = require_roles(Role.ADMIN, Role.EMPLOYEE)

# checklist de termos — itens separados dos conteúdos educativos
TERM_ITEMS = [
    "Li o termo de uso do Compliance Copilot.",
    "Entendi que a IA não substitui a análise humana de compliance.",
    "Entendi que devo inserir apenas dados necessários para a consulta.",
    "Entendi que todas as consultas podem ser auditadas pela equipe de compliance.",
    "Entendi o fluxo de pré-aprovação e quando utilizá-lo.",
]


@router.get("", response_model=list[TrainingItemOut])
def list_training(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items = db.query(TrainingItem).order_by(TrainingItem.order_index).all()
    acked = {
        a.training_item_id
        for a in db.query(UserTrainingAcknowledgement)
        .filter(UserTrainingAcknowledgement.user_id == user.id)
        .all()
    }
    result = []
    for item in items:
        out = TrainingItemOut.model_validate(item)
        out.acknowledged = item.id in acked
        result.append(out)
    return result


@router.post("/acknowledge", status_code=201)
def acknowledge(
    payload: TrainingAcknowledge,
    db: Session = Depends(get_db),
    user: User = Depends(_TRAINING_WRITER),
):
    item = db.get(TrainingItem, payload.training_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item de treinamento não encontrado")

    exists = (
        db.query(UserTrainingAcknowledgement)
        .filter_by(user_id=user.id, training_item_id=payload.training_item_id)
        .first()
    )
    if not exists:
        db.add(UserTrainingAcknowledgement(
            user_id=user.id,
            training_item_id=payload.training_item_id,
        ))
        log_event(
            db, "TRAINING_ACKNOWLEDGED",
            f"{user.email} concluiu: {item.title}",
            user_id=user.id, actor_label=user.email,
            entity="training_items", entity_id=item.id,
        )
        db.commit()
    return {"ok": True}


@router.get("/progress")
def progress(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total = db.query(TrainingItem).count()
    required = db.query(TrainingItem).filter(TrainingItem.required == True).count()  # noqa: E712
    done = (
        db.query(UserTrainingAcknowledgement)
        .filter(UserTrainingAcknowledgement.user_id == user.id)
        .count()
    )
    done_required = (
        db.query(UserTrainingAcknowledgement)
        .join(TrainingItem, UserTrainingAcknowledgement.training_item_id == TrainingItem.id)
        .filter(
            UserTrainingAcknowledgement.user_id == user.id,
            TrainingItem.required == True,  # noqa: E712
        )
        .count()
    )
    return {
        "total": total,
        "required": required,
        "completed": done,
        "completed_required": done_required,
        "all_required_done": done_required >= required,
        "percent": round(done / total * 100) if total else 0,
    }


@router.get("/terms")
def get_terms(_: User = Depends(get_current_user)):
    """Retorna o checklist de termos de uso."""
    return {"terms": TERM_ITEMS}
