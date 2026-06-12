# Architecture

## Overview

Compliance Copilot is a monorepo with three main components:

```
compliance-copilot/
├── backend/          # FastAPI + Python 3.12
├── frontend/         # Next.js 14 + TypeScript
└── docs/             # Architecture and design docs
```

## Backend Layers

```
app/
├── api/
│   ├── deps.py           # JWT auth + RBAC dependency injection
│   └── routes/           # One file per domain (auth, copilot, products, ...)
├── core/
│   ├── config.py         # Pydantic Settings — all config from env vars
│   ├── security.py       # JWT (PyJWT) + bcrypt password hashing
│   └── permissions.py    # Role definitions and access matrix
├── db/
│   ├── base.py           # SQLAlchemy DeclarativeBase + TimestampMixin
│   └── session.py        # Engine + session factory
├── models/               # SQLAlchemy ORM models (one file per domain)
├── schemas/              # Pydantic v2 request/response schemas
├── services/
│   ├── rules_engine.py   # Pure deterministic rules evaluator
│   ├── rag.py            # Chunking + embedding + retrieval
│   ├── ai_provider.py    # AI abstraction (mock / OpenAI)
│   ├── copilot.py        # Orchestration: rules → RAG → AI → persist
│   └── audit.py          # AuditLog helpers + SystemSettings
└── tests/                # pytest suite
```

## Data Flow

```
User question
     │
     ▼
┌─────────────────────────────────────────────────┐
│  Copilot Service (copilot.py)                    │
│                                                  │
│  1. Out-of-scope detection (regex)               │
│  2. Product resolution (by ID or name hint)      │
│  3. Restricted list check                        │
│  4. Rules Engine → AUTHORITATIVE decision        │
│  5. RAG retrieval → supporting chunks            │
│  6. Source enforcement (no source = INCONCLUSIVE)│
│  7. Document conflict check                      │
│  8. AI Provider → justification text only       │
│  9. Persist: query + answer + sources + audit    │
└─────────────────────────────────────────────────┘
     │
     ▼
Structured response: decision + justification + sources + confidence
```

## Security Design

- **Authentication**: JWT Bearer tokens (PyJWT, HS256)
- **Authorization**: Role-based (ADMIN / COMPLIANCE / EMPLOYEE / AUDITOR)
- **Passwords**: bcrypt with salt
- **Secrets**: All from environment variables, never in code
- **CORS**: Restricted to configured origins
- **Upload**: Extension whitelist + 20 MB limit
- **Audit**: Append-only log for all state mutations

## Database Schema

Key entities and relationships:

```
User ──────────────┬── CopilotQuery ── CopilotAnswer ── SourceReference
                   ├── PreApprovalRequest ── PreApprovalComment
                   └── UserTrainingAcknowledgement

FinancialProduct ──── CopilotQuery
ComplianceRule   (evaluated by rules engine, not FK-linked to queries)
PolicyDocument ────── DocumentChunk (embedding JSONB)
AuditLog         (append-only, no FK constraints to allow retention)
SystemSetting    (key-value store for runtime configuration)
RestrictedListItem
```
