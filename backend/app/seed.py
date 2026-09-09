"""Seed script — populates demo data for development.

Run with:  python -m app.seed

Creates four demo users, a portfolio of fictional products, compliance rules,
a policy document (pre-indexed), system settings, and training items.
All personal data used here is entirely fictional.

Demo password: Compliance123!
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.document import PolicyDocument
from app.models.product import FinancialProduct
from app.models.restricted import RestrictedListItem
from app.models.rule import ComplianceRule
from app.models.setting import SystemSetting
from app.models.training import TrainingItem
from app.models.user import User

DEMO_PASSWORD = "Compliance123!"

POLICY_TEXT = """
POLÍTICA DE COMPLIANCE DE INVESTIMENTOS — VERSÃO 2.1

1. OBJETIVO
Esta política estabelece as diretrizes para controle de conflitos de interesse e
operações com valores mobiliários por parte dos colaboradores.

2. FUNDOS ABERTOS
Aplicações de até R$ 100.000 em fundos abertos disponíveis na plataforma são
permitidas sem aprovação prévia ou reporte. Operações acima de R$ 100.000 devem
ser registradas no sistema de controles internos antes de sua execução.

3. AÇÕES
Qualquer operação com ações de companhias listadas exige aprovação prévia do
compliance. A operação só pode ser realizada depois da aprovação.

4. ATIVOS DIGITAIS (CRIPTOMOEDAS)
Operações com criptomoedas são restritas para colaboradores e não devem ser
executadas.

5. LISTA RESTRITA
A lista restrita é atualizada em tempo real pelo compliance. Nenhuma operação
pode ser realizada com ativos nela listados, independentemente do tipo ou valor.

6. PRÉ-APROVAÇÃO
Toda solicitação de pré-aprovação deve conter: ativo, tipo de operação, volume
estimado e justificativa de negócio. A decisão será comunicada em até 48 horas.

7. AUSÊNCIA DE POLÍTICA
Produtos e operações sem regra aplicável devem ser encaminhados ao compliance.
Nenhuma conclusão favorável deve ser presumida na ausência de política suficiente.

8. AUDITORIA
Consultas, decisões automáticas, solicitações e decisões de pré-aprovação são
registradas para fins de auditoria.
"""


def seed(db: Session) -> None:
    # ── users ──────────────────────────────────────────────────────────
    users_data = [
        {"email": "admin@demo.local", "full_name": "Admin Demo", "role": "ADMIN", "department": "TI"},
        {"email": "compliance@demo.local", "full_name": "Carla Compliance", "role": "COMPLIANCE", "department": "Compliance"},
        {"email": "colaborador@demo.local", "full_name": "Pedro Colaborador", "role": "EMPLOYEE", "department": "Gestão"},
        {"email": "auditor@demo.local", "full_name": "Ana Auditora", "role": "AUDITOR", "department": "Auditoria"},
    ]
    for ud in users_data:
        if not db.query(User).filter(User.email == ud["email"]).first():
            db.add(User(hashed_password=hash_password(DEMO_PASSWORD), is_active=True, **ud))
    db.flush()

    # ── products ────────────────────────────────────────────────────────
    products_data = [
        {"name": "Fundo Multimercado Alpha", "product_type": "OPEN_FUND", "identifier": "FMALT", "issuer": "Gestora Alpha", "risk": "MEDIUM", "status": "ALLOWED"},
        {"name": "Fundo de Renda Fixa Beta", "product_type": "OPEN_FUND", "identifier": "FRFBT", "issuer": "Gestora Beta", "risk": "LOW", "status": "ALLOWED"},
        {"name": "Fundo FIP Gamma", "product_type": "CLOSED_FUND", "identifier": "FPGAM", "issuer": "Gestora Gamma", "risk": "HIGH", "status": "MONITORED"},
        {"name": "Ações XPTO3", "product_type": "STOCK", "identifier": "XPTO3", "issuer": "XPTO S.A.", "risk": "HIGH", "status": "ALLOWED"},
        {"name": "Ações ACME3", "product_type": "STOCK", "identifier": "ACME3", "issuer": "ACME S.A.", "risk": "HIGH", "status": "ALLOWED"},
        {"name": "CriptoNova", "product_type": "CRYPTO", "identifier": "CNOVA", "issuer": "CriptoNova Ltd.", "risk": "HIGH", "status": "ALLOWED"},
        {"name": "Lumen DeFi", "product_type": "CRYPTO", "identifier": "LMDFX", "issuer": "Lumen Protocol", "risk": "HIGH", "status": "ALLOWED"},
        {"name": "Debênture Ômega 2028", "product_type": "FIXED_INCOME", "identifier": "OMGDB28", "issuer": "Ômega S.A.", "risk": "LOW", "status": "ALLOWED"},
    ]
    for pd in products_data:
        product = db.query(FinancialProduct).filter(
            FinancialProduct.identifier == pd["identifier"]
        ).first()
        if product:
            for field, value in pd.items():
                setattr(product, field, value)
        else:
            db.add(FinancialProduct(**pd))
    db.flush()

    # ── restricted list ─────────────────────────────────────────────────
    restricted_items = [
        {"identifier": "ACME3", "name": "Ações ACME3", "reason": "Período de silêncio do emissor"},
    ]
    restricted_identifiers = {item["identifier"] for item in restricted_items}
    for legacy_identifier in {"CNOVA", "LMDFX"}:
        legacy = db.query(RestrictedListItem).filter(
            RestrictedListItem.identifier == legacy_identifier
        ).first()
        if legacy and legacy_identifier not in restricted_identifiers:
            legacy.active = False
    for ri in restricted_items:
        item = db.query(RestrictedListItem).filter(
            RestrictedListItem.identifier == ri["identifier"]
        ).first()
        if item:
            item.name = ri["name"]
            item.reason = ri["reason"]
            item.active = True
        else:
            db.add(RestrictedListItem(**ri, active=True))
    db.flush()

    # ── rules ────────────────────────────────────────────────────────────
    rules_data = [
        {"rule_key": "open-funds-allowed", "name": "Fundos abertos permitidos", "product_type": "OPEN_FUND", "decision": "ALLOWED",
         "risk": "LOW", "priority": 10, "description": "Fundos abertos permitidos por padrão."},
        {"rule_key": "open-funds-report-threshold", "name": "Fundos abertos > 100k reportar", "product_type": "OPEN_FUND",
         "condition": {"amount_gt": 100000}, "decision": "REPORT_REQUIRED",
         "risk": "MEDIUM", "priority": 5, "description": "Operações acima de R$100k devem ser reportadas."},
        {"rule_key": "personal-stock-trading", "name": "Ações exigem pré-aprovação", "product_type": "STOCK", "decision": "PRE_APPROVAL_REQUIRED",
         "risk": "MEDIUM", "priority": 10, "description": "Toda operação com ações requer pré-aprovação."},
        {"rule_key": "crypto-restricted", "name": "Criptoativos restritos", "product_type": "CRYPTO", "decision": "RESTRICTED",
         "risk": "HIGH", "priority": 10, "description": "Criptoativos vedados pela política interna."},
    ]
    active_rule_names = {rule["name"] for rule in rules_data}
    for legacy_name in {"Derivativos restritos", "Renda fixa permitida"}:
        legacy = db.query(ComplianceRule).filter(ComplianceRule.name == legacy_name).first()
        if legacy and legacy_name not in active_rule_names:
            legacy.is_active = False
            legacy.status = "ARCHIVED"
    for rd in rules_data:
        data = {**rd, "condition": rd.get("condition", {}), "is_active": True, "status": "ACTIVE", "version": 1, "effective_from": datetime(2026, 1, 1, tzinfo=timezone.utc)}
        configured_rule = db.query(ComplianceRule).filter(
            ComplianceRule.name == rd["name"]
        ).first()
        if configured_rule:
            for field, value in data.items():
                setattr(configured_rule, field, value)
        else:
            db.add(ComplianceRule(**data))
    db.flush()

    # ── policy document ──────────────────────────────────────────────────
    doc = db.query(PolicyDocument).filter(
        PolicyDocument.name == "Política de Investimentos v2.1"
    ).first()
    if not doc:
        doc = PolicyDocument(
            name="Política de Investimentos v2.1",
            doc_type="POLICY",
            version="2.1",
            owner="compliance@demo.local",
            status="ACTIVE",
            extracted_text=POLICY_TEXT,
            uploaded_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
        )
        db.add(doc)
        db.flush()
    else:
        doc.doc_type = "POLICY"
        doc.version = "2.1"
        doc.owner = "compliance@demo.local"
        doc.status = "ACTIVE"
        doc.extracted_text = POLICY_TEXT
        doc.processed_at = datetime.now(timezone.utc)
    from app.services.rag import index_document
    index_document(doc, db)

    # ── system settings ───────────────────────────────────────────────────
    settings_data = [
        ("data_retention_days",      "730",    "Dias de retenção de logs de auditoria (LGPD)"),
        ("pre_approval_sla_hours",   "48",     "SLA capturado na criação de cada pré-aprovação"),
    ]
    obsolete_setting_keys = {
        "human_review_threshold",
        "require_human_high_risk",
        "ai_provider",
        "ai_model",
        "ai_top_k_sources",
        "ai_min_score",
        "ai_require_source",
        "restricted_list_active",
        "session_expire_minutes",
        "max_login_attempts",
        "min_password_length",
        "query_retention_days",
        "auto_anonymize_inactive",
        "allow_data_export",
        "app_name",
    }
    obsolete_settings = db.query(SystemSetting).filter(
        SystemSetting.key.in_(obsolete_setting_keys)
    ).all()
    for obsolete_setting in obsolete_settings:
        db.delete(obsolete_setting)
    for key, value, desc in settings_data:
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            setting.value = value
            setting.description = desc
        else:
            db.add(SystemSetting(key=key, value=value, description=desc))
    db.flush()

    # ── training items ────────────────────────────────────────────────────
    training_data = [
        (1,  "Como usar o Copilot",
             "O Compliance Copilot responde perguntas sobre conformidade de investimentos. Para obter a melhor resposta, informe o tipo de produto, valor estimado e objetivo da operação. A decisão é gerada por um motor de regras estruturado — a IA apenas redige a justificativa.",
             "TOOL"),
        (2,  "Como perguntar corretamente",
             "Seja específico: informe o produto, o valor e a intenção. Exemplo bom: 'Posso comprar R$ 50.000 em cotas do Fundo X?' Exemplo ruim: 'Posso investir?'",
             "TOOL"),
        (3,  "Exemplos de boas perguntas",
             "✅ 'Posso subscrever um FII com R$ 20.000?' ✅ 'Ações da empresa XPTO3 exigem pré-aprovação?' ✅ 'Fundos abertos de renda fixa são permitidos para colaboradores?'",
             "TOOL"),
        (4,  "Exemplos de perguntas ruins",
             "❌ 'Posso investir?' (muito vago) ❌ 'O que você acha de criptomoedas?' (opinião, não compliance) ❌ Perguntas com dados pessoais de terceiros.",
             "TOOL"),
        (5,  "O que NÃO inserir no chat",
             "Não insira: senhas, dados bancários, CPF de clientes, informações confidenciais de terceiros, detalhes de operações não autorizadas ou dados pessoais além do necessário para a consulta de compliance.",
             "PRIVACIDADE"),
        (6,  "Como interpretar as decisões",
             "PERMITIDO: pode prosseguir. REQUER REPORTE: registre conforme exigido pela política antes de executar. REQUER PRÉ-APROVAÇÃO: aguarde aprovação antes de executar. RESTRITO: não execute em hipótese alguma. INCONCLUSIVO: consulte a equipe de compliance.",
             "COMPLIANCE"),
        (7,  "Quando abrir pré-aprovação",
             "Abra uma pré-aprovação quando a resposta do Copilot for REQUER PRÉ-APROVAÇÃO. Aguarde a decisão do compliance antes de executar a operação.",
             "COMPLIANCE"),
        (8,  "Quando solicitar revisão humana",
             "Solicite revisão humana quando a resposta for INCONCLUSIVO ou REQUER PRÉ-APROVAÇÃO. RESTRITO significa não executar; REQUER REPORTE não depende de liberação humana.",
             "COMPLIANCE"),
        (9,  "Limitações da IA",
             "O Copilot não é um advogado nem um consultor financeiro. Ele aplica as regras internas configuradas pela equipe de compliance — não conhece legislação em tempo real, não interpreta contexto subjetivo e pode errar em situações não previstas nas regras.",
             "TOOL"),
        (10, "Uso responsável",
             "Use o Copilot apenas para consultas relacionadas ao seu trabalho. Não tente 'enganar' o sistema com perguntas ambíguas. Lembre-se: todas as consultas são registradas e podem ser auditadas.",
             "ETICA"),
        (11, "Privacidade e LGPD",
             "Suas consultas são armazenadas para fins de auditoria conforme a política definida pela organização. Você pode solicitar ao administrador a exportação ou anonimização dos seus dados a qualquer momento. Não inserimos dados desnecessários e não treinamos modelos externos com seu histórico.",
             "PRIVACIDADE"),
    ]
    for order, title, body, cat in training_data:
        item = db.query(TrainingItem).filter(TrainingItem.title == title).first()
        if item:
            item.body = body
            item.category = cat
            item.order_index = order
            item.required = True
        else:
            db.add(TrainingItem(title=title, body=body, category=cat, order_index=order, required=True))
    db.flush()

    db.commit()
    # Keep CLI output ASCII-safe because the seed is part of the documented
    # Windows setup flow and some PowerShell sessions still use cp1252.
    print("Seed concluido com sucesso.")
    print(f"  Senha demo: {DEMO_PASSWORD}")
    for ud in users_data:
        print(f"  {ud['role']:12s}  {ud['email']}")


def main():
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
