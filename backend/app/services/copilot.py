"""Copilot — orquestração principal.

Fluxo determinístico:
  1. Detectar fora-de-escopo (pergunta não relacionada a compliance/investimentos)
  2. Resolver produto (por ID ou por busca de nome/identificador)
  3. Verificar lista restrita
  4. Rodar motor de regras → decisão AUTORITATIVA
  5. Buscar chunks via RAG
  6. Garantir fonte: sem regra e sem chunk → INCONCLUSIVE
  7. Verificar conflito entre decisão e documentos recuperados
  8. Gerar justificativa via AI provider (não pode alterar decisão)
  9. Persistir consulta, resposta, fontes e AuditLog atomicamente

Invariantes de segurança:
  - RESTRICTED / BLOCKED nunca viram outra decisão
  - IA escreve apenas a justificativa, não escolhe a decisão
  - Fonte nunca é inventada — só chunks efetivamente recuperados
  - Sem fonte suficiente → INCONCLUSIVE obrigatório
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.copilot import CopilotAnswer, CopilotQuery, SourceReference
from app.models.product import FinancialProduct
from app.models.restricted import RestrictedListItem
from app.models.rule import ComplianceRule
from app.schemas.enums import Decision, RiskLevel
from app.services.ai_provider import get_provider
from app.services.audit import get_setting, log_event
from app.services.rag import retrieve
from app.services.rules_engine import EvaluationContext, RuleSpec, evaluate

DISCLAIMER = (
    "\n\n⚠️ A resposta do Compliance Copilot apoia a análise de compliance, "
    "mas não substitui a revisão humana quando exigida pela política interna."
)

_NEXT_ACTION: dict[Decision, str] = {
    Decision.ALLOWED: "Você pode prosseguir com a operação normalmente.",
    Decision.REPORT_REQUIRED: "Registre a operação no sistema de controles internos antes de executar.",
    Decision.PRE_APPROVAL_REQUIRED: "Abra uma solicitação de pré-aprovação antes de realizar a operação.",
    Decision.RESTRICTED: "Esta operação não é permitida pela política interna. Não execute.",
    Decision.INCONCLUSIVE: "Consulte a equipe de compliance antes de prosseguir.",
}

# termos que indicam pergunta dentro do escopo
_SCOPE_TERMS = re.compile(
    r"fund|fundo|ação|ações|stock|ativo|produto|investimento|invest|"
    r"crypto|cripto|derivativo|derivative|ipo|renda|compliance|política|"
    r"operação|operar|comprar|vender|aplicar|resgatar|carteira|portfólio|"
    r"pre[- ]?aprova|pré[- ]?aprova|restrição|restrito|bloqueado|"
    r"permitted|allowed|can i|posso|devo|preciso",
    re.IGNORECASE,
)

_OUT_OF_SCOPE_ANSWER = (
    "Esta pergunta está fora do escopo do Compliance Copilot. "
    "Sou especializado em análise de conformidade de investimentos e produtos financeiros. "
    "Para perguntas sobre compliance de investimentos, reformule a consulta especificando "
    "o produto, operação ou política de interesse."
)


@dataclass
class CopilotInput:
    user_id: int
    question: str
    product_type: str | None = None
    product_id: int | None = None
    product_name_hint: str | None = None  # busca por nome quando ID não é fornecido
    amount: float | None = None
    objective: str | None = None


@dataclass
class CopilotResult:
    query_id: int
    decision: str
    answer: str
    justification: str
    sources: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    risk_level: str = "MEDIUM"
    next_action: str | None = None
    requires_human_review: bool = False
    matched_rules: list[str] = field(default_factory=list)
    out_of_scope: bool = False


def _is_out_of_scope(question: str) -> bool:
    return not bool(_SCOPE_TERMS.search(question))


def _load_rules(db: Session) -> list[RuleSpec]:
    rows = db.query(ComplianceRule).filter(ComplianceRule.is_active == True).all()  # noqa: E712
    return [
        RuleSpec(
            name=r.name,
            decision=Decision(r.decision),
            risk=RiskLevel(r.risk),
            priority=r.priority,
            product_type=r.product_type,
            condition=r.condition or {},
        )
        for r in rows
    ]


def _resolve_product(inp: CopilotInput, db: Session) -> tuple[str | None, str, bool]:
    """Retorna (product_type, product_status, on_restricted_list)."""
    product_type = inp.product_type
    product_status = "ALLOWED"

    # resolve por ID
    if inp.product_id:
        p = db.get(FinancialProduct, inp.product_id)
        if p:
            product_type = p.product_type
            product_status = p.status

    # resolve por hint de nome (busca parcial)
    elif inp.product_name_hint:
        like = f"%{inp.product_name_hint}%"
        p = (
            db.query(FinancialProduct)
            .filter(
                FinancialProduct.name.ilike(like)
                | FinancialProduct.identifier.ilike(like)
            )
            .first()
        )
        if p:
            product_type = p.product_type
            product_status = p.status

    # verifica lista restrita por tipo ou identificador
    on_restricted = False
    if product_type:
        on_restricted = bool(
            db.query(RestrictedListItem)
            .filter(
                RestrictedListItem.active == True,  # noqa: E712
                RestrictedListItem.identifier.ilike(f"%{product_type}%"),
            )
            .first()
        )

    return product_type, product_status, on_restricted


def _confidence(
    decision: Decision,
    matched_rules: list[str],
    sources_count: int,
    out_of_scope: bool,
) -> float:
    if out_of_scope:
        return 0.0
    base = {
        Decision.ALLOWED: 0.80,
        Decision.REPORT_REQUIRED: 0.75,
        Decision.PRE_APPROVAL_REQUIRED: 0.75,
        Decision.RESTRICTED: 0.95,
        Decision.INCONCLUSIVE: 0.40,
    }[decision]
    if matched_rules and "builtin_default" not in matched_rules:
        base += 0.05
    if sources_count >= 2:
        base += 0.05
    return min(round(base, 2), 1.0)


def _check_doc_conflict(decision: Decision, chunks: list) -> bool:
    """Retorna True se documentos recuperados contradizem a decisão do motor.

    Heurística simples: se a decisão é ALLOWED mas documentos contêm
    termos de restrição explícita, há conflito potencial.
    """
    if decision not in (Decision.ALLOWED, Decision.REPORT_REQUIRED):
        return False
    restriction_terms = re.compile(r"\bvedado\b|\bproibido\b|\bnão.*permitido\b|\brestr", re.I)
    return any(restriction_terms.search(c.content) for c in chunks[:3])


def run_query(inp: CopilotInput, db: Session) -> CopilotResult:
    threshold = float(get_setting(db, "human_review_threshold") or "100000")

    # 1. fora de escopo
    if _is_out_of_scope(inp.question):
        query_row = CopilotQuery(
            user_id=inp.user_id,
            question=inp.question,
            product_type=inp.product_type,
            product_id=inp.product_id,
            amount=inp.amount,
            objective=inp.objective,
        )
        db.add(query_row)
        db.flush()
        answer_row = CopilotAnswer(
            query_id=query_row.id,
            decision=Decision.INCONCLUSIVE.value,
            answer=_OUT_OF_SCOPE_ANSWER,
            justification=_OUT_OF_SCOPE_ANSWER,
            risk_level=RiskLevel.LOW.value,
            confidence=0.0,
            next_action="Reformule a pergunta especificando um produto ou operação financeira.",
            requires_human_review=False,
            matched_rules=[],
        )
        db.add(answer_row)
        log_event(
            db, "COPILOT_OUT_OF_SCOPE",
            f"Pergunta fora do escopo: {inp.question[:80]}",
            user_id=inp.user_id, entity="copilot_queries", entity_id=query_row.id,
        )
        db.commit()
        return CopilotResult(
            query_id=query_row.id,
            decision=Decision.INCONCLUSIVE.value,
            answer=_OUT_OF_SCOPE_ANSWER,
            justification=_OUT_OF_SCOPE_ANSWER,
            confidence=0.0,
            risk_level=RiskLevel.LOW.value,
            next_action="Reformule a pergunta especificando um produto ou operação financeira.",
            out_of_scope=True,
        )

    # 2–3. resolver produto e lista restrita
    product_type, product_status, on_restricted = _resolve_product(inp, db)

    # 4. motor de regras
    ctx = EvaluationContext(
        product_type=product_type,
        product_status=product_status,
        on_restricted_list=on_restricted,
        amount=inp.amount,
        human_review_threshold=threshold,
    )
    rules = _load_rules(db)
    result = evaluate(ctx, rules)

    # guarda se decisão foi determinada por hard restriction (nunca sobrescreve)
    hard_restricted = result.decision == Decision.RESTRICTED and (
        on_restricted or product_status in ("RESTRICTED", "BLOCKED")
    )

    # 5. RAG
    search_query = inp.question
    if product_type:
        search_query += f" {product_type}"
    chunks = retrieve(search_query, db)

    # 6. sem fonte → INCONCLUSIVE (exceto hard restrictions que são auto-evidentes)
    has_source = bool(result.matched_rules and result.matched_rules[0] not in ("",)) or bool(chunks)
    if not has_source and not hard_restricted:
        result.decision = Decision.INCONCLUSIVE
        result.reason = "Sem regra configurada ou base documental suficiente para concluir."
        result.risk_level = RiskLevel.MEDIUM
        result.requires_human_review = True

    # 7. conflito documento vs decisão → INCONCLUSIVE (exceto hard restrictions)
    if not hard_restricted and _check_doc_conflict(result.decision, chunks):
        result.decision = Decision.INCONCLUSIVE
        result.reason = "Documentos recuperados contêm termos de restrição que conflitam com a decisão automática."
        result.risk_level = RiskLevel.HIGH
        result.requires_human_review = True

    # 8. justificativa via IA
    system_prompt = (
        "Você é o Compliance Copilot, especialista em conformidade de investimentos. "
        "A decisão estruturada foi determinada pelo motor de regras e é DEFINITIVA — não a contradiga. "
        "Escreva uma justificativa objetiva em português, máximo 4 frases. "
        "Não invente regras. Não cite fontes que não aparecem no contexto. "
        "Não dê garantia jurídica. Não use linguagem de marketing."
    )
    sources_excerpt = "\n".join(
        f"- [{c.document_name}]: {c.content[:200]}" for c in chunks[:3]
    ) or "Nenhum trecho de política recuperado."

    user_prompt = (
        f"Pergunta: {inp.question}\n"
        f"Tipo de produto: {product_type or 'não informado'}\n"
        f"Valor da operação: {f'R$ {inp.amount:,.2f}' if inp.amount else 'não informado'}\n"
        f"Decisão: {result.decision.value}\n"
        f"Motivo do motor: {result.reason}\n"
        f"Regras aplicadas: {', '.join(result.matched_rules) or 'padrão do tipo de produto'}\n"
        f"Trechos de política:\n{sources_excerpt}"
    )
    justification = get_provider().answer(system_prompt, user_prompt)

    answer_text = (
        f"**Decisão: {result.decision.value}**\n\n{justification}{DISCLAIMER}"
    )

    # 9–11. persistência
    query_row = CopilotQuery(
        user_id=inp.user_id,
        question=inp.question,
        product_type=product_type,
        product_id=inp.product_id,
        amount=inp.amount,
        objective=inp.objective,
    )
    db.add(query_row)
    db.flush()

    confidence = _confidence(result.decision, result.matched_rules, len(chunks), False)
    answer_row = CopilotAnswer(
        query_id=query_row.id,
        decision=result.decision.value,
        answer=answer_text,
        justification=justification,
        risk_level=result.risk_level.value,
        confidence=confidence,
        next_action=_NEXT_ACTION.get(result.decision),
        requires_human_review=result.requires_human_review,
        matched_rules=result.matched_rules,
    )
    db.add(answer_row)
    db.flush()

    for chunk in chunks:
        db.add(SourceReference(
            answer_id=answer_row.id,
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            document_name=chunk.document_name,
            excerpt=chunk.content[:400],
            score=chunk.score,
        ))

    log_event(
        db, "COPILOT_QUERY",
        f"Consulta: decisão={result.decision.value} confiança={confidence}",
        user_id=inp.user_id,
        entity="copilot_queries", entity_id=query_row.id,
        meta={
            "decision": result.decision.value,
            "confidence": confidence,
            "product_type": product_type,
            "requires_human_review": result.requires_human_review,
        },
    )
    db.commit()

    return CopilotResult(
        query_id=query_row.id,
        decision=result.decision.value,
        answer=answer_text,
        justification=justification,
        sources=[
            {
                "document_id": c.document_id,
                "chunk_id": c.chunk_id,
                "document_name": c.document_name,
                "excerpt": c.content[:400],
                "score": c.score,
            }
            for c in chunks
        ],
        confidence=confidence,
        risk_level=result.risk_level.value,
        next_action=_NEXT_ACTION.get(result.decision),
        requires_human_review=result.requires_human_review,
        matched_rules=result.matched_rules,
    )
