"""Configurações do sistema por seção."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin, require_compliance
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
    # ── IA ────────────────────────────────────────────────────────────────
    {"key": "ai_provider",         "section": "ia", "label": "Provedor de IA",              "type": "select",  "options": ["mock","openai"], "description": "mock = offline sem API; openai = requer OPENAI_API_KEY"},
    {"key": "ai_model",            "section": "ia", "label": "Modelo OpenAI",               "type": "text",    "description": "Ex: gpt-4o-mini"},
    {"key": "ai_top_k_sources",    "section": "ia", "label": "Top K fontes RAG",            "type": "number",  "description": "Quantidade máxima de chunks recuperados por consulta"},
    {"key": "ai_min_score",        "section": "ia", "label": "Score mínimo de fonte",       "type": "number",  "description": "Fonte abaixo deste score é ignorada (0.0–1.0)"},
    {"key": "ai_require_source",   "section": "ia", "label": "Exigir fonte obrigatória",    "type": "boolean", "description": "Se ativado, consulta sem fonte retorna INCONCLUSIVE"},
    # ── Compliance ────────────────────────────────────────────────────────
    {"key": "human_review_threshold",  "section": "compliance", "label": "Valor mínimo para revisão humana (R$)", "type": "number",  "description": "Operações acima deste valor exigem revisão humana"},
    {"key": "require_human_high_risk", "section": "compliance", "label": "Revisão humana obrigatória (alto risco)", "type": "boolean", "description": "Força revisão humana para decisões de risco ALTO"},
    {"key": "restricted_list_active",  "section": "compliance", "label": "Lista restrita ativa",                   "type": "boolean", "description": "Ativa a checagem contra a lista restrita interna"},
    # ── Segurança ─────────────────────────────────────────────────────────
    {"key": "session_expire_minutes",  "section": "seguranca", "label": "Expiração de sessão (minutos)",   "type": "number",  "description": "Tempo até o token JWT expirar"},
    {"key": "max_login_attempts",      "section": "seguranca", "label": "Tentativas máximas de login",    "type": "number",  "description": "Após este número de falhas o acesso é bloqueado"},
    {"key": "min_password_length",     "section": "seguranca", "label": "Comprimento mínimo de senha",    "type": "number",  "description": "Mínimo de caracteres para novas senhas"},
    # ── LGPD ─────────────────────────────────────────────────────────────
    {"key": "data_retention_days",         "section": "lgpd", "label": "Retenção de logs (dias)",          "type": "number",  "description": "Logs mais antigos que este prazo são removidos pela política de retenção"},
    {"key": "query_retention_days",        "section": "lgpd", "label": "Retenção de consultas (dias)",     "type": "number",  "description": "Consultas ao Copilot são removidas após este prazo"},
    {"key": "auto_anonymize_inactive",     "section": "lgpd", "label": "Anonimização automática",          "type": "boolean", "description": "Anonimiza usuários inativos automaticamente após 365 dias"},
    {"key": "allow_data_export",           "section": "lgpd", "label": "Exportação de dados habilitada",   "type": "boolean", "description": "Permite que admins exportem dados do titular (Art. 18 LGPD)"},
]

SECTION_LABELS = {
    "ia":         "Inteligência Artificial",
    "compliance": "Compliance",
    "seguranca":  "Segurança",
    "lgpd":       "LGPD / Privacidade",
}

# Valores padrão para configurações não encontradas no banco
DEFAULTS: dict[str, str] = {
    "ai_provider":              "mock",
    "ai_model":                 "gpt-4o-mini",
    "ai_top_k_sources":         "4",
    "ai_min_score":             "0.0",
    "ai_require_source":        "false",
    "human_review_threshold":   "100000",
    "require_human_high_risk":  "true",
    "restricted_list_active":   "true",
    "session_expire_minutes":   "480",
    "max_login_attempts":       "5",
    "min_password_length":      "8",
    "data_retention_days":      "730",
    "query_retention_days":     "730",
    "auto_anonymize_inactive":  "false",
    "allow_data_export":        "true",
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
