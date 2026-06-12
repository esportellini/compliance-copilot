"""Módulo de privacidade e LGPD.

Princípios implementados (Lei 13.709/2018):
  Finalidade      — dados tratados apenas para fins de compliance
  Necessidade     — mínimo necessário coletado
  Segurança       — anonimização em vez de exclusão quando há registros vinculados
  Prevenção       — retenção configurável, não infinita
  Transparência   — exportação completa dos dados do titular
  Responsabilização — AuditLog em toda ação de privacidade
  Prestação de contas — relatório de dados tratados disponível ao titular
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.copilot import CopilotQuery
from app.models.pre_approval import PreApprovalRequest
from app.models.user import User
from app.schemas.auth import UserOut
from app.services.audit import get_setting, log_event

router = APIRouter(prefix="/privacy", tags=["privacy"])

# Dados tratados pelo sistema — exibidos na interface para transparência
DATA_INVENTORY = [
    {
        "categoria": "Dados de identificação",
        "campos": ["nome completo", "e-mail"],
        "finalidade": "Autenticação e identificação do colaborador",
        "base_legal": "Legítimo interesse — controle interno de compliance",
        "retencao": "Enquanto o vínculo empregatício estiver ativo",
    },
    {
        "categoria": "Consultas ao Copilot",
        "campos": ["pergunta", "produto consultado", "valor", "decisão"],
        "finalidade": "Registro de consultas de compliance para auditoria regulatória",
        "base_legal": "Obrigação legal — regulação de mercado de capitais",
        "retencao": "Configurável (padrão: 730 dias)",
    },
    {
        "categoria": "Pré-aprovações",
        "campos": ["produto", "operação", "valor", "justificativa"],
        "finalidade": "Controle de operações com potencial conflito de interesse",
        "base_legal": "Obrigação legal",
        "retencao": "Configurável (padrão: 730 dias)",
    },
    {
        "categoria": "Logs de auditoria",
        "campos": ["evento", "data/hora", "IP não coletado", "ação realizada"],
        "finalidade": "Rastreabilidade para auditoria interna e regulatória",
        "base_legal": "Obrigação legal",
        "retencao": "Configurável (padrão: 730 dias); logs críticos nunca excluídos",
    },
]

MINIMIZATION_CHECKLIST = [
    "Não coletamos dados de localização",
    "Não coletamos dados biométricos",
    "Não coletamos dados de saúde",
    "Não coletamos dados além do necessário para compliance",
    "Não compartilhamos dados com terceiros sem base legal",
    "Não treinamos modelos externos com dados dos usuários automaticamente",
    "Não salvamos chaves de API em código-fonte",
    "Não salvamos prompts sensíveis além do necessário para auditoria",
    "Logs de auditoria não contêm senhas ou tokens",
]


@router.get("/info")
def privacy_info(_: User = Depends(get_current_user)):
    """Retorna inventário de dados, finalidades e checklist de minimização."""
    return {
        "principios_lgpd": [
            {"nome": "Finalidade", "descricao": "Dados tratados apenas para fins de compliance e auditoria regulatória."},
            {"nome": "Necessidade", "descricao": "Coletamos apenas o mínimo necessário para cada finalidade."},
            {"nome": "Segurança", "descricao": "Dados protegidos por autenticação JWT, RBAC e hash bcrypt."},
            {"nome": "Prevenção", "descricao": "Política de retenção configurável evita acúmulo desnecessário."},
            {"nome": "Transparência", "descricao": "Titular pode exportar todos os seus dados a qualquer momento."},
            {"nome": "Responsabilização", "descricao": "Toda ação de privacidade gera registro de auditoria imutável."},
            {"nome": "Prestação de contas", "descricao": "Relatório de dados tratados disponível para o DPO."},
        ],
        "dados_tratados": DATA_INVENTORY,
        "minimizacao": MINIMIZATION_CHECKLIST,
    }


@router.get("/user-data/{user_id}")
def export_user_data(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    """Exporta todos os dados vinculados ao titular (Art. 18 LGPD)."""
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    queries = db.query(CopilotQuery).filter(CopilotQuery.user_id == user_id).all()
    pre_approvals = db.query(PreApprovalRequest).filter(
        PreApprovalRequest.requester_id == user_id
    ).all()
    audit_events = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(200)
        .all()
    )

    log_event(
        db, "USER_DATA_EXPORTED",
        f"Exportação de dados do usuário {user_id} ({u.email}) por {actor.email}",
        user_id=actor.id, actor_label=actor.email,
        entity="users", entity_id=user_id,
        severity="WARNING",
        meta={"target_user_id": user_id, "target_email": u.email},
    )
    db.commit()

    return {
        "titular": UserOut.model_validate(u),
        "dados_pessoais": {
            "email": u.email if not u.is_anonymized else "[anonimizado]",
            "nome": u.full_name if not u.is_anonymized else "[anonimizado]",
            "departamento": u.department,
            "papel": u.role,
            "ativo": u.is_active,
            "anonimizado": u.is_anonymized,
            "cadastrado_em": str(u.created_at),
        },
        "consultas_copilot": [
            {
                "id": q.id,
                "pergunta": q.question,
                "produto_tipo": q.product_type,
                "valor": q.amount,
                "data": str(q.created_at),
            }
            for q in queries
        ],
        "pre_aprovacoes": [
            {
                "id": p.id,
                "produto": p.product_label,
                "operacao": p.operation_type,
                "status": p.status,
                "data": str(p.created_at),
            }
            for p in pre_approvals
        ],
        "eventos_auditoria": [
            {
                "id": a.id,
                "tipo": a.event_type,
                "mensagem": a.message,
                "data": str(a.created_at),
            }
            for a in audit_events
        ],
        "totais": {
            "consultas": len(queries),
            "pre_aprovacoes": len(pre_approvals),
            "eventos_auditoria": len(audit_events),
        },
    }


@router.post("/anonymize-user/{user_id}")
def anonymize_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    """Anonimiza dados pessoais do titular (Art. 18 VI LGPD).

    Não excluímos registros de auditoria com fins regulatórios — anonimizamos
    os campos de identificação pessoal, preservando o registro do evento.
    """
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if u.id == actor.id:
        raise HTTPException(status_code=400, detail="Você não pode anonimizar sua própria conta")
    if u.is_anonymized:
        raise HTTPException(status_code=400, detail="Usuário já está anonimizado")
    if u.is_active:
        raise HTTPException(
            status_code=400,
            detail="Desative o usuário antes de anonimizar. Usuários ativos não podem ser anonimizados.",
        )

    original_email = u.email
    u.email = f"anonimizado_{user_id}@removido.local"
    u.full_name = "Usuário Anonimizado"
    u.hashed_password = ""
    u.department = None
    u.is_anonymized = True

    log_event(
        db, "USER_ANONYMIZED",
        f"Usuário {user_id} anonimizado por {actor.email} (e-mail original preservado apenas neste log)",
        user_id=actor.id, actor_label=actor.email,
        entity="users", entity_id=user_id,
        severity="WARNING",
        meta={"target_id": user_id, "original_email_hash": str(hash(original_email))},
    )
    db.commit()
    return {"ok": True, "message": f"Usuário {user_id} anonimizado com sucesso."}


@router.post("/run-retention-policy")
def run_retention(
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    """Executa política de retenção de dados (Art. 15 LGPD).

    Remove logs de auditoria não críticos mais antigos que o prazo configurado.
    Logs críticos (USER_ANONYMIZED, PRE_APPROVAL_DECISION) nunca são removidos.
    """
    days = int(get_setting(db, "data_retention_days") or "730")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # eventos protegidos — nunca podem ser removidos por política de retenção
    protected = {
        "USER_ANONYMIZED", "PRE_APPROVAL_DECISION", "PRODUCT_BLOCKED",
        "PRODUCT_RESTRICTED", "USER_DEACTIVATED", "RETENTION_RUN",
    }

    deleted = (
        db.query(AuditLog)
        .filter(
            AuditLog.created_at < cutoff,
            ~AuditLog.event_type.in_(protected),
            AuditLog.severity != "CRITICAL",
        )
        .delete(synchronize_session=False)
    )

    log_event(
        db, "RETENTION_RUN",
        f"Retenção executada por {actor.email}: {deleted} registros removidos (cutoff: {cutoff.date()})",
        user_id=actor.id, actor_label=actor.email,
        severity="WARNING",
        meta={
            "deleted_count": deleted,
            "retention_days": days,
            "cutoff_date": str(cutoff.date()),
            "protected_events": list(protected),
        },
    )
    db.commit()
    return {
        "ok": True,
        "deleted_audit_logs": deleted,
        "retention_days": days,
        "cutoff_date": str(cutoff.date()),
        "protected_events_preserved": list(protected),
    }
