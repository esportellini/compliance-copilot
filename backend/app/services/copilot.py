"""Copilot — orquestração principal.

Fluxo determinístico:
  1. Resolver produto (por ID ou por busca exata de nome/identificador)
  2. Verificar hard restrictions do produto concreto
  3. Detectar fora-de-escopo quando não há hard restriction
  4. Rodar motor de regras → decisão AUTORITATIVA
  5. Buscar chunks via RAG
  6. Manter INCONCLUSIVE quando não há regra aplicável
  7. Gerar justificativa via AI provider (não pode alterar decisão)
  8. Persistir consulta, resposta, fontes e AuditLog atomicamente

Invariantes de segurança:
  - RESTRICTED / BLOCKED nunca viram outra decisão
  - IA escreve apenas a justificativa, não escolhe a decisão
  - Fonte nunca é inventada — só chunks efetivamente recuperados
  - RAG fornece evidência e não escolhe a decisão
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.identifiers import normalize_identifier, normalized_identifier_expression
from app.models.copilot import CopilotAnswer, CopilotQuery, SourceReference
from app.models.product import FinancialProduct
from app.models.restricted import RestrictedListItem
from app.models.rule import ComplianceRule
from app.schemas.enums import Decision, RiskLevel
from app.services.ai_provider import get_provider, safe_explanation
from app.services.audit import log_event
from app.services.rag import build_retrieval_query, retrieve
from app.services.rules_engine import EvaluationContext, EvaluationResult, RuleSpec, evaluate

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
    rule_provenance: list[dict] = field(default_factory=list)
    out_of_scope: bool = False


@dataclass
class ProductResolution:
    product: FinancialProduct | None
    product_type: str | None
    product_status: str
    on_restricted_list: bool
    error: str | None = None


def _is_out_of_scope(question: str) -> bool:
    return not bool(_SCOPE_TERMS.search(question))


def _eligible_rule_rows(db: Session, evaluated_at: datetime) -> list[ComplianceRule]:
    return db.query(ComplianceRule).filter(
        ComplianceRule.is_active == True,  # noqa: E712
        ComplianceRule.status == "ACTIVE",
        ComplianceRule.effective_from <= evaluated_at,
        or_(ComplianceRule.effective_to.is_(None), ComplianceRule.effective_to > evaluated_at),
    ).all()


def _load_rules(rows: list[ComplianceRule]) -> list[RuleSpec]:
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


def _provenance(rows: list[ComplianceRule], matched_names: list[str]) -> list[dict]:
    matched = set(matched_names)
    candidates = [row for row in rows if row.name in matched]
    if not candidates:
        return []
    winning_priority = min(row.priority for row in candidates)
    return [
        {
            "rule_id": row.id,
            "rule_key": row.rule_key,
            "version": row.version,
            "name": row.name,
            "priority": row.priority,
            "decision": row.decision,
            "condition": row.condition or {},
        }
        for row in sorted(candidates, key=lambda item: (item.name, item.id or 0))
        if row.priority == winning_priority
    ]


def _resolve_product(inp: CopilotInput, db: Session) -> ProductResolution:
    """Resolve one concrete product without silently choosing ambiguous matches."""
    product_type = inp.product_type
    product_status = "ALLOWED"
    product: FinancialProduct | None = None

    # ID is authoritative when present.
    if inp.product_id is not None:
        product = db.get(FinancialProduct, inp.product_id)
        if product is None:
            return ProductResolution(
                product=None,
                product_type=None,
                product_status="ALLOWED",
                on_restricted_list=False,
                error=f"Produto informado não encontrado: id={inp.product_id}.",
            )

    # Otherwise resolve an exact ticker first, then an exact product name.
    elif inp.product_name_hint:
        normalized_identifier = normalize_identifier(inp.product_name_hint)
        if normalized_identifier is None:
            return ProductResolution(
                product=None,
                product_type=None,
                product_status="ALLOWED",
                on_restricted_list=False,
                error="Produto informado não encontrado.",
            )
        identifier_matches = (
            db.query(FinancialProduct)
            .filter(
                normalized_identifier_expression(FinancialProduct.identifier)
                == normalized_identifier
            )
            .order_by(FinancialProduct.id.asc())
            .limit(2)
            .all()
        )
        if len(identifier_matches) > 1:
            return ProductResolution(
                product=None,
                product_type=None,
                product_status="ALLOWED",
                on_restricted_list=False,
                error="Identificador de produto ambíguo.",
            )
        if identifier_matches:
            product = identifier_matches[0]
        else:
            normalized_name = inp.product_name_hint.strip().lower()
            name_matches = (
                db.query(FinancialProduct)
                .filter(func.lower(func.trim(FinancialProduct.name)) == normalized_name)
                .order_by(FinancialProduct.id.asc())
                .limit(2)
                .all()
            )
            if len(name_matches) > 1:
                return ProductResolution(
                    product=None,
                    product_type=None,
                    product_status="ALLOWED",
                    on_restricted_list=False,
                    error="Nome de produto ambíguo.",
                )
            if name_matches:
                product = name_matches[0]
            else:
                return ProductResolution(
                    product=None,
                    product_type=None,
                    product_status="ALLOWED",
                    on_restricted_list=False,
                    error="Produto informado não encontrado.",
                )

    if product:
        product_type = product.product_type
        product_status = product.status

    # The restricted list identifies a concrete asset, never a product category.
    on_restricted = False
    if product and product.identifier:
        on_restricted = bool(
            db.query(RestrictedListItem)
            .filter(
                RestrictedListItem.active == True,  # noqa: E712
                normalized_identifier_expression(RestrictedListItem.identifier)
                == normalize_identifier(product.identifier),
            )
            .order_by(RestrictedListItem.id.asc())
            .first()
        )

    return ProductResolution(
        product=product,
        product_type=product_type,
        product_status=product_status,
        on_restricted_list=on_restricted,
    )


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
    if matched_rules:
        base += 0.05
    if sources_count >= 2:
        base += 0.05
    return min(round(base, 2), 1.0)


def run_query(inp: CopilotInput, db: Session) -> CopilotResult:
    # 1–2. Resolve concrete products before scope so hard restrictions cannot be bypassed.
    resolution = _resolve_product(inp, db)
    hard_restricted = bool(
        resolution.product
        and (
            resolution.on_restricted_list
            or resolution.product_status in {"BLOCKED", "RESTRICTED"}
        )
    )

    # 3. Fora de escopo remains an early return when no objective hard restriction exists.
    if not hard_restricted and resolution.error is None and _is_out_of_scope(inp.question):
        query_row = CopilotQuery(
            user_id=inp.user_id,
            question=inp.question,
            product_type=resolution.product_type,
            product_id=resolution.product.id if resolution.product else None,
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
            requires_human_review=True,
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
            requires_human_review=True,
            out_of_scope=True,
        )

    # 4. Product-resolution failures are explicit and never fall back to client type.
    if resolution.error:
        result = EvaluationResult(
            decision=Decision.INCONCLUSIVE,
            reason=resolution.error,
            matched_rules=[],
            risk_level=RiskLevel.MEDIUM,
            requires_human_review=True,
        )
    else:
        ctx = EvaluationContext(
            product_type=resolution.product_type,
            product_status=resolution.product_status,
            on_restricted_list=resolution.on_restricted_list,
            amount=inp.amount,
        )
        rule_rows = _eligible_rule_rows(db, datetime.now(timezone.utc))
        result = evaluate(ctx, _load_rules(rule_rows))

    rule_provenance = _provenance(rule_rows, result.matched_rules) if resolution.error is None else []

    # 5. RAG
    search_query = build_retrieval_query(
        inp.question,
        product_name=resolution.product.name if resolution.product else inp.product_name_hint,
        identifier=resolution.product.identifier if resolution.product else None,
        product_type=resolution.product_type,
    )
    chunks = retrieve(search_query, db)

    # 6. A matched structured rule is itself sufficient policy information.
    has_source = bool(result.matched_rules) or bool(chunks)
    if not has_source and resolution.error is None:
        result.decision = Decision.INCONCLUSIVE
        result.reason = "Sem regra configurada ou base documental suficiente para concluir."
        result.risk_level = RiskLevel.MEDIUM
        result.requires_human_review = True

    # 7. The provider receives the engine decision as structured input.
    provider = get_provider()
    candidate = provider.answer(
        decision=result.decision,
        product_type=resolution.product_type,
        deterministic_reason=result.reason,
        question=inp.question,
        evidence_excerpts=[c.content[:200] for c in chunks[:3]],
    )
    justification = safe_explanation(
        result.decision,
        resolution.product_type,
        result.reason,
        candidate,
    )

    answer_text = (
        f"**Decisão: {result.decision.value}**\n\n{justification}{DISCLAIMER}"
    )

    # 8. persistência
    query_row = CopilotQuery(
        user_id=inp.user_id,
        question=inp.question,
        product_type=resolution.product_type,
        product_id=resolution.product.id if resolution.product else None,
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
        rule_provenance=rule_provenance,
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
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            document_version=chunk.document_version,
        ))

    log_event(
        db, "COPILOT_QUERY",
        f"Consulta: decisão={result.decision.value} confiança={confidence}",
        user_id=inp.user_id,
        entity="copilot_queries", entity_id=query_row.id,
        meta={
            "decision": result.decision.value,
            "confidence": confidence,
            "product_type": resolution.product_type,
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
                "page_number": c.page_number,
                "section_title": c.section_title,
                "document_version": c.document_version,
            }
            for c in chunks
        ],
        confidence=confidence,
        risk_level=result.risk_level.value,
        next_action=_NEXT_ACTION.get(result.decision),
        requires_human_review=result.requires_human_review,
        matched_rules=result.matched_rules,
        rule_provenance=rule_provenance,
    )
