# Product Case

## Problem

Asset managers, family offices, and investment advisors employ people who
interact with financial markets daily. These employees face a recurring
compliance challenge: **"Am I allowed to make this investment?"**

The typical answer involves:
1. Finding and reading the internal investment policy (often 20+ pages)
2. Checking if the product is on a restricted or watch list
3. Determining if pre-approval is required
4. Deciding whether to report the operation

This process is slow, error-prone, and inconsistently applied.

## Solution

Compliance Copilot provides an internal tool that:
1. Accepts natural-language questions about specific operations
2. Runs a **deterministic rules engine** against configured policies
3. Retrieves supporting excerpts from indexed policy documents (RAG)
4. Returns a **structured decision** with justification and next action
5. Logs everything for audit

The AI component writes the justification in natural language — it cannot
change the engine's decision, which is always authoritative.

## Differentiation vs Generic Chatbot

| Generic AI Chatbot | Compliance Copilot |
|--------------------|-------------------|
| Generates text freely | Decision from rules engine |
| No source citation | Cites actual policy documents |
| No audit trail | Full append-only audit log |
| No compliance workflow | Pre-approval + review flows |
| Hallucination risk | INCONCLUSIVE when uncertain |
| No role-based access | RBAC for 4 personas |

## Key Design Decisions

1. **Rules engine is authoritative** — the LLM cannot override RESTRICTED.
2. **No source = INCONCLUSIVE** — the system never guesses without evidence.
3. **Offline mode** — works fully without any external API key (mock provider).
4. **Append-only audit** — logs cannot be deleted by normal operation.
5. **LGPD-compliant** — anonymization, export, and retention built in.

## Target Users

- **Compliance Officer** — configures rules, reviews pre-approvals, monitors activity
- **Portfolio Manager / Analyst** — queries about specific operations
- **Auditor** — read-only access to all history and audit logs
- **Administrator** — user management, system settings
