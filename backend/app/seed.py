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
from app.db.init_db import init_db
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
Aplicações em fundos abertos disponíveis na plataforma são permitidas sem necessidade
de aprovação prévia, desde que respeitados os limites individuais de concentração.
Operações acima de R$ 100.000 devem ser reportadas ao compliance no dia seguinte.

3. AÇÕES E DERIVATIVOS
Qualquer operação com ações de companhias listadas ou derivativos sobre esses
ativos exige aprovação prévia do compliance. A solicitação deve ser enviada com
pelo menos dois dias úteis de antecedência.

4. ATIVOS DIGITAIS (CRIPTOMOEDAS)
Operações com criptomoedas são restritas para colaboradores, dada a elevada
volatilidade e ausência de regulação específica aplicável à atividade da firma.

5. LISTA RESTRITA
A lista restrita é atualizada em tempo real pelo compliance. Nenhuma operação
pode ser realizada com ativos nela listados, independentemente do tipo ou valor.

6. PRÉ-APROVAÇÃO
Toda solicitação de pré-aprovação deve conter: ativo, tipo de operação, volume
estimado e justificativa de negócio. A decisão será comunicada em até 48 horas.

7. REGISTRO E REPORTE
Todas as operações realizadas por colaboradores devem ser reportadas ao sistema
de controles internos no mesmo dia. A omissão é considerada falta grave.
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
        {"name": "CriptoNova", "product_type": "CRYPTO", "identifier": "CNOVA", "issuer": "CriptoNova Ltd.", "risk": "HIGH", "status": "RESTRICTED"},
        {"name": "Lumen DeFi", "product_type": "CRYPTO", "identifier": "LMDFX", "issuer": "Lumen Protocol", "risk": "HIGH", "status": "RESTRICTED"},
        {"name": "Debênture Ômega 2028", "product_type": "FIXED_INCOME", "identifier": "OMGDB28", "issuer": "Ômega S.A.", "risk": "LOW", "status": "ALLOWED"},
    ]
    for pd in products_data:
        if not db.query(FinancialProduct).filter(FinancialProduct.identifier == pd["identifier"]).first():
            db.add(FinancialProduct(**pd))
    db.flush()

    # ── restricted list ─────────────────────────────────────────────────
    restricted_items = [
        {"identifier": "CNOVA", "name": "CriptoNova", "reason": "Ativo sem liquidez auditável"},
        {"identifier": "LMDFX", "name": "Lumen DeFi", "reason": "Regulação pendente — vedado por política"},
    ]
    for ri in restricted_items:
        if not db.query(RestrictedListItem).filter(RestrictedListItem.identifier == ri["identifier"]).first():
            db.add(RestrictedListItem(**ri, active=True))
    db.flush()

    # ── rules ────────────────────────────────────────────────────────────
    rules_data = [
        {"name": "Fundos abertos permitidos", "product_type": "OPEN_FUND", "decision": "ALLOWED",
         "risk": "LOW", "priority": 10, "description": "Fundos abertos permitidos por padrão."},
        {"name": "Fundos abertos > 100k reportar", "product_type": "OPEN_FUND",
         "condition": {"amount_gt": 100000}, "decision": "REPORT_REQUIRED",
         "risk": "MEDIUM", "priority": 5, "description": "Operações acima de R$100k devem ser reportadas."},
        {"name": "Ações exigem pré-aprovação", "product_type": "STOCK", "decision": "PRE_APPROVAL_REQUIRED",
         "risk": "MEDIUM", "priority": 10, "description": "Toda operação com ações requer pré-aprovação."},
        {"name": "Derivativos restritos", "product_type": "DERIVATIVE", "decision": "RESTRICTED",
         "risk": "HIGH", "priority": 5, "description": "Derivativos não permitidos para colaboradores."},
        {"name": "Criptoativos restritos", "product_type": "CRYPTO", "decision": "RESTRICTED",
         "risk": "HIGH", "priority": 1, "description": "Criptoativos vedados pela política interna."},
        {"name": "Renda fixa permitida", "product_type": "FIXED_INCOME", "decision": "ALLOWED",
         "risk": "LOW", "priority": 10, "description": "Renda fixa pública e privada grau de investimento permitida."},
    ]
    for rd in rules_data:
        if not db.query(ComplianceRule).filter(ComplianceRule.name == rd["name"]).first():
            db.add(ComplianceRule(condition=rd.pop("condition", {}), is_active=True, **rd))
    db.flush()

    # ── policy document ──────────────────────────────────────────────────
    if not db.query(PolicyDocument).filter(PolicyDocument.name == "Política de Investimentos v2.1").first():
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
        from app.services.rag import index_document
        index_document(doc, db)

    # ── system settings ───────────────────────────────────────────────────
    settings_data = [
        ("human_review_threshold",   "100000", "Valor (R$) acima do qual exige revisão humana"),
        ("data_retention_days",      "730",    "Dias de retenção de logs de auditoria (LGPD)"),
        ("query_retention_days",     "730",    "Dias de retenção de consultas ao Copilot"),
        ("ai_provider",              "mock",   "Provedor de IA: mock ou openai"),
        ("ai_top_k_sources",         "4",      "Quantidade de chunks RAG por consulta"),
        ("ai_min_score",             "0.0",    "Score mínimo de fonte (0.0–1.0)"),
        ("ai_require_source",        "false",  "Exigir fonte para responder"),
        ("require_human_high_risk",  "true",   "Revisão humana obrigatória para alto risco"),
        ("restricted_list_active",   "true",   "Lista restrita ativa"),
        ("session_expire_minutes",   "480",    "Minutos até o token JWT expirar"),
        ("max_login_attempts",       "5",      "Tentativas máximas de login antes do bloqueio"),
        ("min_password_length",      "8",      "Comprimento mínimo de senha"),
        ("auto_anonymize_inactive",  "false",  "Anonimização automática de usuários inativos"),
        ("allow_data_export",        "true",   "Exportação de dados habilitada (LGPD Art. 18)"),
        ("app_name",                 "Compliance Copilot", "Nome exibido na interface"),
    ]
    for key, value, desc in settings_data:
        if not db.query(SystemSetting).filter(SystemSetting.key == key).first():
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
             "PERMITIDO: pode prosseguir. REQUER REPORTE: execute e registre no mesmo dia. REQUER PRÉ-APROVAÇÃO: aguarde aprovação antes de executar. RESTRITO: não execute em hipótese alguma. INCONCLUSIVO: consulte a equipe de compliance.",
             "COMPLIANCE"),
        (7,  "Quando abrir pré-aprovação",
             "Abra uma pré-aprovação sempre que a resposta do Copilot for REQUER PRÉ-APROVAÇÃO, quando o valor superar o limite configurado, ou quando houver dúvida sobre a conformidade da operação.",
             "COMPLIANCE"),
        (8,  "Quando solicitar revisão humana",
             "Solicite revisão humana quando: a resposta for INCONCLUSIVO, o risco for ALTO, o valor for expressivo, ou quando a situação for incomum e não coberta pelas regras existentes.",
             "COMPLIANCE"),
        (9,  "Limitações da IA",
             "O Copilot não é um advogado nem um consultor financeiro. Ele aplica as regras internas configuradas pela equipe de compliance — não conhece legislação em tempo real, não interpreta contexto subjetivo e pode errar em situações não previstas nas regras.",
             "TOOL"),
        (10, "Uso responsável",
             "Use o Copilot apenas para consultas relacionadas ao seu trabalho. Não tente 'enganar' o sistema com perguntas ambíguas. Lembre-se: todas as consultas são registradas e podem ser auditadas.",
             "ETICA"),
        (11, "Privacidade e LGPD",
             "Suas consultas são armazenadas para fins de auditoria regulatória (base legal: obrigação legal). Você pode solicitar ao administrador a exportação ou anonimização dos seus dados a qualquer momento. Não inserimos dados desnecessários e não treinamos modelos externos com seu histórico.",
             "PRIVACIDADE"),
    ]
    for order, title, body, cat in training_data:
        if not db.query(TrainingItem).filter(TrainingItem.title == title).first():
            db.add(TrainingItem(title=title, body=body, category=cat, order_index=order, required=True))
    db.flush()

    db.commit()
    print("✓ Seed concluído com sucesso.")
    print(f"  Senha demo: {DEMO_PASSWORD}")
    for ud in users_data:
        print(f"  {ud['role']:12s}  {ud['email']}")


def main():
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
