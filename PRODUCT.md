# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- Compliance officers review operations, configure deterministic rules and
  maintain policy evidence during their daily work.
- Employees and portfolio analysts check whether a proposed operation is
  allowed and request pre-approval when required.
- Auditors inspect persisted decisions, sources and the audit trail without
  performing mutations.
- Administrators manage users, privacy operations, training and system settings.

## Product Purpose

Compliance Copilot is an internal demonstration workspace for evaluating
financial operations against structured compliance rules, attaching relevant
documentary evidence and routing cases that require a human decision. Success
means that each result is understandable, actionable and traceable.

## Positioning

Rules decide, retrieval provides evidence, AI explains, humans approve when
required, and the material steps remain auditable. The rules engine is the sole
authority for the structured decision; retrieval and AI never change it.

## Operating Context

Users work with product identifiers, operation values, internal policies,
pre-approval queues, comments, decisions, reports and audit events. The product
is a desktop-first B2B application that must also remain usable on tablet and
mobile web. It is an educational portfolio project populated with fictional
demo data.

## Capabilities and Constraints

- Existing FastAPI contracts, RBAC, deterministic rule semantics, BM25
  retrieval, optional OpenAI refinement and approval state machine are fixed.
- Five decision states are supported: `ALLOWED`, `REPORT_REQUIRED`,
  `PRE_APPROVAL_REQUIRED`, `RESTRICTED` and `INCONCLUSIVE`.
- Offline retrieval is deterministic lexical BM25. AI is an explanation layer.
- The frontend uses Next.js 14, React, TypeScript, Tailwind CSS, TanStack Query,
  Lucide and Recharts. No new UI framework or backend endpoint is planned.
- Portuguese product language must remain concise, consistent and professional.
- The public portfolio release is feature-complete; future work should preserve
  these boundaries unless a requirement explicitly changes them.

## Brand Commitments

- Product name: Compliance Copilot.
- Personality: trustworthy, precise, controlled, secure, traceable,
  institutional and modern without looking experimental.
- The interface is light-first with an institutional deep-green accent.
- The product must resemble a financial operating system rather than a generic
  dashboard, chatbot, crypto interface or futuristic AI product.

## Evidence on Hand

The repository contains working API integrations, role-scoped navigation,
fictional demo accounts, seeded example products and policies, and complete
Employee, Compliance, Auditor and Admin flows. Public documentation must use
only behavior demonstrated by the code and fictional data; it must not imply
customer adoption or production deployment.

## Product Principles

1. Make the structured decision visually primary.
2. Keep rules, explanation and evidence visibly distinct.
3. Present approvals as an operational queue with clear ownership and status.
4. Favor dense, calm and auditable interfaces over decorative presentation.
5. Preserve role boundaries in navigation and available actions.

## Accessibility & Inclusion

The web interface must provide semantic controls and tables, keyboard-visible
focus, accessible names for icon-only actions, readable contrast, explicit text
labels for status, and functional responsive behavior without relying on color
alone.
