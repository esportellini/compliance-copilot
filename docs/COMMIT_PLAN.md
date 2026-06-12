# Commit Plan

Suggested commit history for a clean GitHub portfolio presentation.

## Initial Setup

```
feat: initialize monorepo with FastAPI + Next.js + Docker
chore: add .gitignore, .env.example, requirements.txt
```

## Backend Foundation

```
feat(auth): JWT authentication with bcrypt password hashing
feat(rbac): role-based access control for 4 user personas
feat(models): SQLAlchemy models for all 12 domain entities
feat(audit): append-only audit log with event types
```

## Core Features

```
feat(rules-engine): deterministic compliance evaluation engine
feat(rag): document chunking, embedding, and retrieval pipeline
feat(copilot): orchestration layer — rules → RAG → AI → persist
feat(products): product catalog with restricted/blocked status
feat(documents): policy document upload, extraction, and indexing
feat(pre-approvals): approval workflow with comments and timeline
```

## Supporting Features

```
feat(reports): aggregated analytics endpoints with CSV export
feat(privacy): LGPD module — export, anonymization, retention
feat(training): onboarding module with progress tracking
feat(settings): system configuration by section
feat(seed): realistic demo data with 4 user personas
```

## Frontend

```
feat(ui): Next.js 14 app with Tailwind and TanStack Query
feat(login): authentication flow with protected routes
feat(dashboard): metrics overview with Recharts
feat(copilot-ui): query interface with decision card and sources
feat(history): query history with filters
feat(products-ui): product catalog with create/edit/restrict/block
feat(documents-ui): document management with drag-and-drop upload
feat(rules-ui): rule management with simulate modal
feat(pre-approvals-ui): approval workflow with timeline
feat(audit-ui): audit trail with filters and CSV export
feat(reports-ui): analytics dashboard with charts
feat(privacy-ui): LGPD tools and data inventory
feat(training-ui): training modules with checklist
feat(settings-ui): configuration sections with toggle inputs
```

## Quality

```
test: auth, permissions, rules engine, copilot, privacy
docs: architecture, RAG pipeline, rule engine, security, LGPD
chore: production hardening — global error handler, CORS, no hardcoded secrets
```
