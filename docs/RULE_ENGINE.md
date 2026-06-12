# Rule Engine

## Overview

The rules engine is the authoritative decision-maker. The AI layer cannot
override its output — it can only write the natural-language justification.

## Evaluation Order

```
1. Hard restrictions (always RESTRICTED, never overridable)
   ├── Product on restricted list
   └── Product status = BLOCKED or RESTRICTED

2. Configured rules (from database)
   ├── Filter: active rules matching product_type (or null = all types)
   ├── Filter: condition matches (e.g. amount_gt: 100000)
   ├── Sort by priority (ascending — lower = higher priority)
   ├── Conflict at same priority → INCONCLUSIVE
   └── Most restrictive wins among applicable rules

3. Manual-review product types (no rule needed)
   └── CLOSED_FUND, EXCLUSIVE_FUND → INCONCLUSIVE + human review

4. Built-in defaults by product type
   ├── OPEN_FUND, FIXED_INCOME → ALLOWED
   ├── STOCK, IPO → PRE_APPROVAL_REQUIRED
   ├── DERIVATIVE, CRYPTO → RESTRICTED
   └── (others) → falls through

5. No type, no rule → INCONCLUSIVE (never guesses)
```

## Human Review Triggers

A result sets `requires_human_review = True` when:
- Amount exceeds the configured threshold (default: R$ 100,000)
- Decision is RESTRICTED, INCONCLUSIVE, or PRE_APPROVAL_REQUIRED
- Conflict detected between rules at same priority

## Rule Conditions (JSON schema)

```json
{ "amount_gt": 100000 }        // fires when amount > 100000
{ "amount_gte": 50000 }        // fires when amount >= 50000
{ "status": "MONITORED" }      // fires when product has this status
{ "product_type": "STOCK" }    // fires for this product type
{}                             // no condition — always fires
```

## Invariant

**RESTRICTED is terminal.** No downstream processing (AI, document source,
conflict check) can change a RESTRICTED decision. This is enforced in both
the rules engine and the copilot orchestration layer.
