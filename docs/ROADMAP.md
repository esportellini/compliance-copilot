# Roadmap

## v1.0 — Public portfolio release

- [x] Authentication (JWT + bcrypt)
- [x] RBAC (Admin / Compliance / Employee / Auditor)
- [x] Deterministic rules engine
- [x] Deterministic offline BM25 retrieval with optional OpenAI embeddings
- [x] Copilot query flow with decision + justification + sources
- [x] Product catalog with restricted/blocked status
- [x] Policy document upload (PDF, DOCX, TXT) + chunking
- [x] Pre-approval workflow with comments and timeline
- [x] Append-only audit trail
- [x] Reports and dashboard
- [x] LGPD module (export, anonymization, retention)
- [x] Training and onboarding module
- [x] Runtime setting for audit-log retention
- [x] Reproducible Docker Compose setup with Alembic bootstrap
- [x] Linux CI for backend and frontend quality gates

## Possible next steps

- Notifications for pre-approval status changes.
- SSO, MFA, rate limiting and deployment-specific security controls.
- Multi-tenant data isolation and finer-grained permissions.
- External restricted-list integrations and signed audit exports.
- A dedicated vector store only if corpus size and measured retrieval quality
  justify the additional operational complexity.

These are product options, not commitments. The current release deliberately
keeps retrieval lightweight and the decision path deterministic.
