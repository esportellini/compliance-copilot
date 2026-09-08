"""Behavioral tests for the deterministic compliance rules engine."""
import pytest

from app.schemas.enums import Decision, RiskLevel
from app.services.rules_engine import EvaluationContext, RuleSpec, evaluate


def ctx(**overrides) -> EvaluationContext:
    values = {
        "product_type": "OPEN_FUND",
        "product_status": "ALLOWED",
        "on_restricted_list": False,
        "amount": None,
    }
    values.update(overrides)
    return EvaluationContext(**values)


def rule(
    name: str,
    decision: Decision,
    *,
    priority: int = 10,
    product_type: str | None = "OPEN_FUND",
    condition: dict | None = None,
) -> RuleSpec:
    risk = {
        Decision.ALLOWED: RiskLevel.LOW,
        Decision.REPORT_REQUIRED: RiskLevel.MEDIUM,
        Decision.PRE_APPROVAL_REQUIRED: RiskLevel.MEDIUM,
        Decision.RESTRICTED: RiskLevel.HIGH,
        Decision.INCONCLUSIVE: RiskLevel.MEDIUM,
    }[decision]
    return RuleSpec(
        name=name,
        decision=decision,
        risk=risk,
        priority=priority,
        product_type=product_type,
        condition=condition or {},
    )


# A missing short-circuit would let the configured ALLOWED rule relax the block.
@pytest.mark.parametrize(
    ("context", "matched_rule"),
    [
        (ctx(on_restricted_list=True), "restricted_list"),
        (ctx(product_status="BLOCKED"), "product_status"),
        (ctx(product_status="RESTRICTED"), "product_status"),
    ],
)
def test_hard_restriction_is_terminal(context, matched_rule):
    result = evaluate(context, [rule("allow_everything", Decision.ALLOWED, priority=1)])

    assert result.decision == Decision.RESTRICTED
    assert result.matched_rules == [matched_rule]
    assert result.requires_human_review is False


# Reintroducing a hard-coded policy for any known type would make one case non-inconclusive.
@pytest.mark.parametrize(
    "product_type",
    ["OPEN_FUND", "STOCK", "CRYPTO", "DERIVATIVE", "FIXED_INCOME", None],
)
def test_no_applicable_rule_is_inconclusive(product_type):
    result = evaluate(ctx(product_type=product_type), [])

    assert result.decision == Decision.INCONCLUSIVE
    assert result.matched_rules == []
    assert result.requires_human_review is True


def test_matching_configured_rule_determines_decision():
    result = evaluate(
        ctx(amount=50_000),
        [rule("open_fund_allowed", Decision.ALLOWED, condition={"amount_gte": 0})],
    )

    assert result.decision == Decision.ALLOWED
    assert result.matched_rules == ["open_fund_allowed"]


# If severity from a lower-precedence rule leaks into the result, this becomes RESTRICTED.
def test_only_highest_precedence_priority_influences_decision():
    rules = [
        rule("lower_precedence_restriction", Decision.RESTRICTED, priority=20),
        rule("winning_allowance", Decision.ALLOWED, priority=10),
    ]

    result = evaluate(ctx(), rules)

    assert result.decision == Decision.ALLOWED
    assert result.matched_rules == ["winning_allowance"]


def test_rule_result_does_not_depend_on_input_order():
    rules = [
        rule("zeta", Decision.ALLOWED, priority=10),
        rule("alpha", Decision.ALLOWED, priority=10),
        rule("ignored", Decision.RESTRICTED, priority=20),
    ]

    first = evaluate(ctx(), rules)
    second = evaluate(ctx(), list(reversed(rules)))

    assert first == second
    assert first.matched_rules == ["alpha", "zeta"]


def test_different_decisions_at_winning_priority_are_inconclusive():
    rules = [
        rule("allow", Decision.ALLOWED, priority=5),
        rule("report", Decision.REPORT_REQUIRED, priority=5),
        rule("ignored", Decision.RESTRICTED, priority=10),
    ]

    result = evaluate(ctx(), rules)

    assert result.decision == Decision.INCONCLUSIVE
    assert result.matched_rules == ["allow", "report"]
    assert result.requires_human_review is True


def test_condition_filters_rule_before_priority_is_selected():
    rules = [
        rule(
            "report_over_100k",
            Decision.REPORT_REQUIRED,
            priority=5,
            condition={"amount_gt": 100_000},
        ),
        rule("allow_open_fund", Decision.ALLOWED, priority=10),
    ]

    below_limit = evaluate(ctx(amount=100_000), rules)
    above_limit = evaluate(ctx(amount=100_000.01), rules)

    assert below_limit.decision == Decision.ALLOWED
    assert above_limit.decision == Decision.REPORT_REQUIRED


@pytest.mark.parametrize(
    "condition",
    [
        {"amount_gr": 100_000},
        {"amount_gt": "100000"},
        {"amount_gte": True},
        {"status": 123},
    ],
)
def test_invalid_rule_condition_fails_closed(condition):
    result = evaluate(
        ctx(amount=200_000),
        [rule("invalid", Decision.ALLOWED, priority=1, condition=condition)],
    )

    assert result.decision == Decision.INCONCLUSIVE
    assert result.matched_rules == []


def test_supported_conditions_can_be_combined():
    result = evaluate(
        ctx(product_type="STOCK", product_status="MONITORED", amount=100_000),
        [
            rule(
                "combined",
                Decision.PRE_APPROVAL_REQUIRED,
                product_type="STOCK",
                condition={
                    "status": "MONITORED",
                    "product_type": "STOCK",
                    "amount_gt": 50_000,
                    "amount_gte": 100_000,
                },
            )
        ],
    )

    assert result.decision == Decision.PRE_APPROVAL_REQUIRED
    assert result.matched_rules == ["combined"]


@pytest.mark.parametrize(
    ("decision", "requires_human_review"),
    [
        (Decision.ALLOWED, False),
        (Decision.REPORT_REQUIRED, False),
        (Decision.PRE_APPROVAL_REQUIRED, True),
        (Decision.RESTRICTED, False),
        (Decision.INCONCLUSIVE, True),
    ],
)
def test_human_review_means_waiting_for_a_human_decision(
    decision, requires_human_review
):
    result = evaluate(ctx(), [rule("policy", decision)])

    assert result.requires_human_review is requires_human_review
