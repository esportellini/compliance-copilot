# Roadmap

## v1.0 — MVP (current)

- [x] Authentication (JWT + bcrypt)
- [x] RBAC (Admin / Compliance / Employee / Auditor)
- [x] Deterministic rules engine
- [x] RAG with offline mock embeddings
- [x] Copilot query flow with decision + justification + sources
- [x] Product catalog with restricted/blocked status
- [x] Policy document upload (PDF, DOCX, TXT) + chunking
- [x] Pre-approval workflow with comments and timeline
- [x] Append-only audit trail
- [x] Reports and dashboard
- [x] LGPD module (export, anonymization, retention)
- [x] Training and onboarding module
- [x] System settings (IA, Compliance, Security, LGPD)
- [x] Docker Compose local setup

## v1.1 — Notifications

- [ ] Email notifications for pre-approval status changes
- [ ] In-app notification bell
- [ ] Compliance digest email (daily/weekly summary)
- [ ] Webhook support for external integrations

## v1.2 — Enhanced RAG

- [ ] Switch from JSONB to pgvector for embedding storage
- [ ] Hybrid search (BM25 + vector)
- [ ] Re-ranking step before answer generation
- [ ] Chunk overlap for better context continuity
- [ ] Support for larger documents (streaming extraction)

## v1.3 — Advanced Compliance

- [ ] Multi-firm support (tenancy)
- [ ] Rule templates library
- [ ] Scheduled rule evaluation reports
- [ ] Integration with CVM/B3 restricted list feeds
- [ ] Pre-trade compliance check API

## v2.0 — Enterprise

- [ ] SSO (SAML / OIDC)
- [ ] Fine-grained permissions at department level
- [ ] Workflow engine for multi-step approvals
- [ ] External audit export (PDF with digital signature)
- [ ] MFA for admin actions
- [ ] Rate limiting per user (Redis-backed)
- [ ] Horizontal scaling (stateless backend)
