"""Rules engine unit tests — pure, no DB required."""
import pytest

from app.schemas.enums import Decision, RiskLevel
from app.services.rules_engine import EvaluationContext, RuleSpec, evaluate


def ctx(**kw) -> EvaluationContext:
    defaults = dict(
        product_type="OPEN_FUND",
        product_status="ALLOWED",
        on_restricted_list=False,
        amount=None,
        human_review_threshold=100_000.0,
    )
    defaults.update(kw)
    return EvaluationContext(**defaults)


# ── restricted invariant ───────────────────────────────────────────────────────

def test_restricted_list_always_restricted():
    result = evaluate(ctx(on_restricted_list=True), [])
    assert result.decision == Decision.RESTRICTED
    assert result.requires_human_review is True


def test_blocked_product_always_restricted():
    result = evaluate(ctx(product_status="BLOCKED"), [])
    assert result.decision == Decision.RESTRICTED


def test_restricted_status_always_restricted():
    result = evaluate(ctx(product_status="RESTRICTED"), [])
    assert result.decision == Decision.RESTRICTED


def test_restricted_cannot_be_overridden_by_rule():
    """A rule saying ALLOWED must NOT override a BLOCKED product."""
    rules = [RuleSpec(name="allow_all", decision=Decision.ALLOWED,
                      risk=RiskLevel.LOW, priority=1, product_type="OPEN_FUND")]
    result = evaluate(ctx(product_type="OPEN_FUND", product_status="BLOCKED"), rules)
    assert result.decision == Decision.RESTRICTED


# ── built-in defaults ──────────────────────────────────────────────────────────

def test_open_fund_default_allowed():
    assert evaluate(ctx(product_type="OPEN_FUND"), []).decision == Decision.ALLOWED


def test_stock_default_preapproval():
    assert evaluate(ctx(product_type="STOCK"), []).decision == Decision.PRE_APPROVAL_REQUIRED


def test_crypto_default_restricted():
    assert evaluate(ctx(product_type="CRYPTO"), []).decision == Decision.RESTRICTED


def test_derivative_default_restricted():
    assert evaluate(ctx(product_type="DERIVATIVE"), []).decision == Decision.RESTRICTED


def test_ipo_default_preapproval():
    assert evaluate(ctx(product_type="IPO"), []).decision == Decision.PRE_APPROVAL_REQUIRED


def test_fixed_income_default_allowed():
    assert evaluate(ctx(product_type="FIXED_INCOME"), []).decision == Decision.ALLOWED


# ── configured rules ───────────────────────────────────────────────────────────

def test_configured_rule_overrides_default():
    rules = [RuleSpec(name="open_fund_report", decision=Decision.REPORT_REQUIRED,
                      risk=RiskLevel.MEDIUM, priority=5, product_type="OPEN_FUND",
                      condition={"amount_gt": 100_000})]
    result = evaluate(ctx(product_type="OPEN_FUND", amount=150_000), rules)
    assert result.decision == Decision.REPORT_REQUIRED
    assert "open_fund_report" in result.matched_rules


def test_most_restrictive_rule_wins():
    rules = [
        RuleSpec(name="r_allowed", decision=Decision.ALLOWED, risk=RiskLevel.LOW, priority=20),
        RuleSpec(name="r_restrict", decision=Decision.PRE_APPROVAL_REQUIRED, risk=RiskLevel.MEDIUM, priority=10),
    ]
    result = evaluate(ctx(product_type="OPEN_FUND"), rules)
    assert result.decision == Decision.PRE_APPROVAL_REQUIRED


def test_conflict_same_priority_is_inconclusive():
    rules = [
        RuleSpec(name="r_a", decision=Decision.ALLOWED, risk=RiskLevel.LOW, priority=10),
        RuleSpec(name="r_b", decision=Decision.REPORT_REQUIRED, risk=RiskLevel.MEDIUM, priority=10),
    ]
    result = evaluate(ctx(product_type="OPEN_FUND"), rules)
    assert result.decision == Decision.INCONCLUSIVE


# ── amount threshold ───────────────────────────────────────────────────────────

def test_amount_above_threshold_requires_review():
    result = evaluate(ctx(product_type="OPEN_FUND", amount=200_000), [])
    assert result.requires_human_review is True


def test_amount_below_threshold_no_forced_review():
    result = evaluate(ctx(product_type="OPEN_FUND", amount=50_000), [])
    assert result.requires_human_review is False


# ── inconclusive ───────────────────────────────────────────────────────────────

def test_no_type_is_inconclusive():
    result = evaluate(ctx(product_type=None), [])
    assert result.decision == Decision.INCONCLUSIVE
    assert result.requires_human_review is True


def test_closed_fund_requires_manual_review():
    result = evaluate(ctx(product_type="CLOSED_FUND"), [])
    assert result.decision == Decision.INCONCLUSIVE
    assert result.requires_human_review is True
