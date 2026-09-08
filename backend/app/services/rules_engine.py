"""Structured compliance rules engine.

The engine is deliberately pure: it takes a context object and a list of rules
and returns a decision. No database access here, which keeps it trivial to unit
test and means the same logic runs in the API, in tests, and in the seed script.

The central invariant the product depends on:

    A structured restrictive decision (RESTRICTED) can never be relaxed by the
    LLM layer downstream. The engine is the source of truth; the model only adds
    natural language and supporting sources on top of it.
"""
from dataclasses import dataclass, field

from app.schemas.enums import Decision, RiskLevel

_RISK_SEVERITY = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
}

_HUMAN_DECISION_REQUIRED = {
    Decision.PRE_APPROVAL_REQUIRED,
    Decision.INCONCLUSIVE,
}

_SUPPORTED_CONDITIONS = {"status", "product_type", "amount_gt", "amount_gte"}


@dataclass
class RuleSpec:
    """A configured ComplianceRule reduced to what the engine needs."""

    name: str
    decision: Decision
    risk: RiskLevel
    priority: int
    product_type: str | None = None
    condition: dict = field(default_factory=dict)


@dataclass
class EvaluationContext:
    product_type: str | None = None
    product_status: str | None = None  # ALLOWED / MONITORED / RESTRICTED / BLOCKED
    on_restricted_list: bool = False
    amount: float | None = None


@dataclass
class EvaluationResult:
    decision: Decision
    reason: str
    matched_rules: list[str]
    risk_level: RiskLevel
    requires_human_review: bool


def _condition_matches(condition: dict, ctx: EvaluationContext) -> bool:
    """A rule fires when every key in its condition is satisfied."""
    if not condition:
        return True
    if not isinstance(condition, dict) or not set(condition).issubset(
        _SUPPORTED_CONDITIONS
    ):
        return False
    if "status" in condition and not isinstance(condition["status"], str):
        return False
    if "product_type" in condition and not isinstance(
        condition["product_type"], str
    ):
        return False
    for key in ("amount_gt", "amount_gte"):
        if key in condition and (
            isinstance(condition[key], bool)
            or not isinstance(condition[key], (int, float))
        ):
            return False
    if "status" in condition and ctx.product_status != condition["status"]:
        return False
    if "product_type" in condition and ctx.product_type != condition["product_type"]:
        return False
    if "amount_gt" in condition and not (ctx.amount or 0) > condition["amount_gt"]:
        return False
    if "amount_gte" in condition and not (ctx.amount or 0) >= condition["amount_gte"]:
        return False
    return True


def evaluate(ctx: EvaluationContext, rules: list[RuleSpec]) -> EvaluationResult:
    # 1. Hard restrictions short-circuit everything. The AI can never relax these.
    if ctx.on_restricted_list:
        return EvaluationResult(
            decision=Decision.RESTRICTED,
            reason="Ativo presente na lista restrita interna.",
            matched_rules=["restricted_list"],
            risk_level=RiskLevel.HIGH,
            requires_human_review=False,
        )
    if ctx.product_status in {"BLOCKED", "RESTRICTED"}:
        return EvaluationResult(
            decision=Decision.RESTRICTED,
            reason=f"Produto com status {ctx.product_status} no catálogo.",
            matched_rules=["product_status"],
            risk_level=RiskLevel.HIGH,
            requires_human_review=False,
        )

    # 2. Configured rules. Consider generic rules and rules for this product type.
    applicable = [
        r
        for r in rules
        if (r.product_type in (None, ctx.product_type)) and _condition_matches(r.condition, ctx)
    ]
    applicable.sort(key=lambda r: (r.priority, r.name))

    if applicable:
        winning_priority = applicable[0].priority
        winning_rules = [r for r in applicable if r.priority == winning_priority]
        distinct = {r.decision for r in winning_rules}
        matched_rules = [r.name for r in winning_rules]

        # Different decisions at the winning priority are a real policy conflict.
        if len(distinct) > 1:
            return EvaluationResult(
                decision=Decision.INCONCLUSIVE,
                reason="Regras de mesma prioridade com decisões conflitantes.",
                matched_rules=matched_rules,
                risk_level=RiskLevel.MEDIUM,
                requires_human_review=True,
            )

        decision = winning_rules[0].decision
        risk = max(
            (r.risk for r in winning_rules),
            key=lambda value: _RISK_SEVERITY[value],
        )
        return EvaluationResult(
            decision=decision,
            reason=f"Regra(s) aplicada(s): {', '.join(matched_rules)}.",
            matched_rules=matched_rules,
            risk_level=risk,
            requires_human_review=decision in _HUMAN_DECISION_REQUIRED,
        )

    # 3. No configured policy applies, so the engine cannot decide safely.
    return EvaluationResult(
        decision=Decision.INCONCLUSIVE,
        reason="Não há regra ou tipo de produto suficiente para decidir com segurança.",
        matched_rules=[],
        risk_level=RiskLevel.MEDIUM,
        requires_human_review=True,
    )
