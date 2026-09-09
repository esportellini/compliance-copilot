# Compliance Copilot

Aplicação interna de demonstração para decisões de compliance sobre operações
financeiras, com regras determinísticas, evidência documental, pré-aprovação
humana e trilha de auditoria.

> Projeto educacional e de portfólio. Não representa aconselhamento jurídico,
> regulatório ou financeiro e não deve ser usado em produção sem revisão.

## Why

Responder “posso executar esta operação?” normalmente exige consultar políticas,
identificar restrições, aplicar regras internas e registrar o resultado. O
Compliance Copilot reúne esse fluxo em uma aplicação auditável e reproduzível.

## Core idea

**Rules decide. Retrieval provides evidence. AI explains. Humans approve when
required. Everything important is auditable.**

- O motor de regras é a única fonte da decisão estruturada.
- Hard restrictions são terminais e avaliadas antes das regras configuradas.
- O modo offline recupera evidências com BM25 lexical determinístico.
- Embeddings OpenAI, quando configurados, apenas refinam o ranking lexical.
- RAG e IA nunca alteram decisão, regras aplicadas ou próxima ação.
- Sem regra aplicável, o resultado é `INCONCLUSIVE`.

## Architecture

```text
Next.js frontend
       │ HTTP/JSON
       ▼
FastAPI API ── JWT/RBAC ── AuditLog
       │
       ├── product resolution + hard restrictions
       ├── deterministic rules engine ── authoritative decision
       ├── BM25 retrieval ── documentary evidence
       └── mock/OpenAI provider ── explanation only
       │
       ▼
PostgreSQL 16 ── schema managed by Alembic
```

## Main flow

```text
Employee asks Copilot
→ rules produce the decision
→ retrieval attaches relevant policy excerpts
→ explanation is persisted with sources
→ PRE_APPROVAL_REQUIRED opens a linked request
→ Compliance reviews, comments and decides
→ Employee sees the outcome
→ the complete flow remains auditable
```

## Features

- JWT authentication and RBAC for Admin, Compliance, Employee and Auditor.
- Product resolution by canonical ID, ticker or exact normalized name.
- Configurable compliance rules with strict numeric priority.
- Restricted-list and product-status hard restrictions.
- PDF, DOCX and TXT ingestion with page/section metadata.
- Deterministic BM25 retrieval and optional OpenAI embedding refinement.
- Structured Copilot responses with sources, confidence and next action.
- Linked pre-approval workflow with explicit state machine and comments.
- Append-only operational audit trail.
- Dashboard and reports scoped by role.
- Demo modules for LGPD, training and audit-log retention.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2.
- **Frontend:** Next.js 14, React 18, TypeScript, Tailwind CSS, TanStack Query.
- **Data:** PostgreSQL 16; SQLite in-memory only for isolated tests.
- **Infrastructure:** Docker Compose and GitHub Actions.

## Quick start

Requirements: Git and Docker with Docker Compose.

```bash
git clone https://github.com/esportellini/compliance-copilot.git
cd compliance-copilot
cp .env.example .env
docker compose up --build
```

No PowerShell, use o comando `Copy-Item .env.example .env` no lugar de `cp`.

The official Compose flow waits for PostgreSQL, runs `alembic upgrade head`,
starts the backend, waits for `/health`, and then starts the frontend. Migration
failure stops the backend. The PostgreSQL data is persisted in the `pgdata`
volume. Seed is deliberately separate; after the services are healthy, run in
another terminal:

```bash
docker compose exec backend python -m app.seed
```

Open:

- Frontend: <http://localhost:3000>
- API documentation: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Alembic is the only schema source for application databases. The seed assumes
that migrations have already run and performs deterministic upserts of fictional
demo data. `Base.metadata.create_all` is restricted to the isolated SQLite test
fixture and is never used by runtime, development or demo startup.

## Environment

The default `.env.example` runs fully offline with `AI_PROVIDER=mock`; no API key
is required. `SECRET_KEY` is an obvious placeholder and must be replaced outside
local demonstration use.

| Variable | Required | Purpose |
|---|---:|---|
| `DATABASE_URL` | Yes | SQLAlchemy connection used by backend and Alembic |
| `SECRET_KEY` | Yes | JWT signing key; replace the placeholder |
| `ENVIRONMENT` | No | `local`, `staging` or `production`; production hides API docs |
| `JWT_ALGORITHM` | No | JWT algorithm, default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Token lifetime, default 480 minutes |
| `CORS_ORIGINS` | No | Comma-separated allowed browser origins |
| `AI_PROVIDER` | No | `mock` by default or `openai` |
| `OPENAI_API_KEY` | OpenAI only | External provider credential |
| `OPENAI_MODEL` | OpenAI only | Explanation model |
| `NEXT_PUBLIC_API_URL` | No | Browser-visible API URL embedded in frontend build |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Compose | Local PostgreSQL container configuration |

## Demo accounts

All accounts use `Compliance123!`.

| Account | Role |
|---|---|
| `admin@demo.local` | Admin |
| `compliance@demo.local` | Compliance |
| `colaborador@demo.local` | Employee |
| `auditor@demo.local` | Auditor, read-only |

These are public, fictional and intentionally insecure demo credentials. Never
reuse them in a real environment.

## Demo flow

1. Sign in as `colaborador@demo.local`.
2. Ask the Copilot whether you may buy `XPTO3`.
3. Inspect `PRE_APPROVAL_REQUIRED`, the matched rule and document metadata.
4. Open the linked pre-approval, select the operation type and submit it.
5. Sign in as `compliance@demo.local`, add a comment and start review.
6. Record a final decision with the required opinion or conditions.
7. Return as the Employee and inspect the decision and persisted timeline.
8. Sign in as `auditor@demo.local` to inspect the audit trail read-only.

## Quality commands

Backend:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\python -m pip install -r requirements-dev.txt
# macOS/Linux: .venv/bin/python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app alembic
alembic upgrade head
python -m app.seed
```

Frontend:

```bash
cd frontend
npm ci
npm run typecheck
npm run lint
npm run build
```

GitHub Actions runs these checks on Linux for every push and pull request. The
frontend Docker image retains Next.js `standalone` output. Some Windows setups
cannot create its symlinks locally; Linux CI is the supported build gate.

## Architecture decisions

- [Architecture](docs/ARCHITECTURE.md)
- [Rule engine](docs/RULE_ENGINE.md)
- [RAG pipeline](docs/RAG_PIPELINE.md)
- [Security and RBAC](docs/SECURITY.md)
- [API overview](docs/API_OVERVIEW.md)
- [LGPD and privacy](docs/LGPD_AND_PRIVACY.md)
- [Product case](docs/PRODUCT_CASE.md)
- [Roadmap](docs/ROADMAP.md)

## Limitations

- Educational demo with fictional rules and policies.
- No rate limiting, MFA, SSO, notifications or multi-tenancy.
- Embeddings, when enabled, are stored as JSONB rather than in a vector database.
- PDF extraction requires selectable text; OCR is not implemented.
- No automated retention for Copilot queries.
- Production operation requires independent security, legal and compliance review.

## Roadmap

The next phase is a frontend redesign. Longer-term possibilities are listed in
[docs/ROADMAP.md](docs/ROADMAP.md) and remain outside the current implementation.

## License

Released under the [MIT License](LICENSE). Copyright © 2026 Enzo.
