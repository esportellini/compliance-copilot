"""Configurações do sistema por seção."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.permissions import Role
from app.db.session import get_db
from app.models.setting import SystemSetting
from app.models.user import User
from app.schemas.common import SettingOut
from app.services.audit import log_event

router = APIRouter(prefix="/settings", tags=["settings"])

# Definição canônica das configurações agrupadas por seção.
# Compliance pode ler tudo mas só admin altera.
SETTING_DEFINITIONS: list[dict] = [
    {"key": "data_retention_days",         "section": "lgpd", "label": "Retenção de logs (dias)",          "type": "number",  "description": "Logs mais antigos que este prazo são removidos pela política de retenção"},
    {"key": "pre_approval_sla_hours",      "section": "workflow", "label": "SLA de pré-aprovação (horas)", "type": "number", "description": "Prazo capturado quando uma nova solicitação é criada"},
]

SECTION_LABELS = {
    "lgpd":       "LGPD / Privacidade",
    "workflow":   "Fluxo operacional",
}

# Valores padrão para configurações não encontradas no banco
DEFAULTS: dict[str, str] = {
    "data_retention_days":      "730",
    "pre_approval_sla_hours":   "48",
}


def _get_all(db: Session) -> dict[str, str]:
    rows = db.query(SystemSetting).all()
    stored = {r.key: r.value for r in rows}
    return {k: stored.get(k, DEFAULTS.get(k, "")) for k in DEFAULTS}


@router.get("")
def list_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retorna todas as configurações agrupadas por seção.
    Compliance e Auditor veem os valores mas não podem alterar.
    Employee não acessa.
    """
    if Role(user.role) == Role.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Acesso negado")

    values = _get_all(db)
    sections: dict[str, list] = {k: [] for k in SECTION_LABELS}

    for defn in SETTING_DEFINITIONS:
        section = defn["section"]
        sections[section].append({
            **defn,
            "value": values.get(defn["key"], DEFAULTS.get(defn["key"], "")),
        })

    return {
        "sections": [
            {
                "key": k,
                "label": SECTION_LABELS[k],
                "settings": sections[k],
                "can_edit": Role(user.role) == Role.ADMIN,
            }
            for k in SECTION_LABELS
        ]
    }


@router.put("/{key}")
def update_setting(
    key: str,
    value: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    if key not in DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Configuração desconhecida: {key}")
    if key == "pre_approval_sla_hours":
        try:
            if int(value) <= 0 or int(value) > 8760:
                raise ValueError
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="SLA deve ser um inteiro entre 1 e 8760 horas") from exc

    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    defn = next((d for d in SETTING_DEFINITIONS if d["key"] == key), {})
    old_value = row.value if row else DEFAULTS.get(key, "")

    if row:
        row.value = value
    else:
        db.add(SystemSetting(
            key=key,
            value=value,
            description=defn.get("description"),
        ))

    log_event(
        db, "SETTING_CHANGED",
        f"Configuração '{key}' alterada por {actor.email}: '{old_value}' → '{value}'",
        user_id=actor.id, actor_label=actor.email,
        severity="WARNING",
        meta={"key": key, "old_value": old_value, "new_value": value},
    )
    db.commit()
    return {"key": key, "value": value}
