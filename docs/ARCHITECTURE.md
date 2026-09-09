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
│   ├── rag.py            # Structured chunking + BM25/hybrid retrieval
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
│  1. Resolve product by ID or exact normalized key │
│  2. Check hard restrictions for concrete product │
│  3. Apply the out-of-scope gate                   │
│  4. Rules Engine → AUTHORITATIVE decision         │
│  5. RAG retrieval → supporting evidence           │
│  6. AI Provider → explanation of that decision    │
│  7. Persist: query + answer + sources + audit      │
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
CopilotQuery ──────── PreApprovalRequest (optional trace, ON DELETE SET NULL)
ComplianceRule   (evaluated by rules engine, not FK-linked to queries)
PolicyDocument ────── DocumentChunk (optional embedding stored as JSONB)
AuditLog         (append-only in normal flows; optional user reference)
SystemSetting    (key-value store for runtime configuration)
RestrictedListItem
```

## Database bootstrap

Alembic is the only schema bootstrap for application databases. The official
Compose command runs `alembic upgrade head` before starting Uvicorn and aborts
if migration fails. The seed assumes the schema is already migrated and only
upserts fictional demo data.

Tests are intentionally separate: their isolated in-memory SQLite fixture uses
`Base.metadata.create_all` and drops the schema after each test. That fixture is
test infrastructure and is never imported by runtime, development or demo code.
