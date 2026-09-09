# Security

## Authentication

- **Protocol**: JWT Bearer (HS256)
- **Library**: PyJWT 2.x
- **Token expiry**: Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 8h)
- **Password hashing**: bcrypt via the `bcrypt` library

## Authorization (RBAC)

| Resource          | ADMIN | COMPLIANCE | EMPLOYEE | AUDITOR |
|-------------------|-------|------------|----------|---------|
| Users (write)     | ✅    | ❌         | ❌       | ❌      |
| Products (write)  | ✅    | ✅         | ❌       | ❌      |
| Rules (write)     | ✅    | ✅         | ❌       | ❌      |
| Documents (write) | ✅    | ✅         | ❌       | ❌      |
| Copilot (query)   | ✅    | ✅         | ✅ (own) | ❌      |
| Pre-approvals     | ✅    | ✅ (all)   | ✅ (own) | 👁️ read |
| Audit logs        | ✅    | 👁️ read   | ❌       | 👁️ read |
| Reports           | ✅    | ✅         | ✅ (own) | 👁️ read |
| Settings (write)  | ✅    | ❌         | ❌       | ❌      |
| Privacy tools     | ✅    | ❌         | ❌       | ❌      |

## Secrets Management

- Runtime secrets are supplied through environment variables. The only
  hardcoded credential is the public, fictional demo password documented below.
- `.env` is in `.gitignore` and never committed
- `SECRET_KEY` must be generated per environment: `python -c "import secrets; print(secrets.token_hex(32))"`

## Input Validation

- All request bodies validated by Pydantic v2 schemas
- File uploads: extension whitelist (`.pdf`, `.docx`, `.txt`) + 20 MB limit
- Email validation relaxed for internal `.local` domains in login schema
- SQL injection: prevented by SQLAlchemy ORM (parameterized queries)

## CORS

- Restricted to origins listed in `CORS_ORIGINS` env variable
- Default: `http://localhost:3000`
- Production: set to exact domain, never `*`

## Audit Trail

- Principal domain operations and security-sensitive mutations generate an
  `AuditLog` entry
- Logs are append-only in normal operation
- Retention policy removes non-critical logs after configured days
- Protected events (anonymization, blocking, pre-approval decisions) are never auto-deleted

## Production Checklist

- [ ] Generate new `SECRET_KEY` (never use the default)
- [ ] Set `ENVIRONMENT=production` (hides Swagger docs)
- [ ] Set `CORS_ORIGINS` to exact domain
- [ ] Configure HTTPS (reverse proxy: nginx / Caddy)
- [ ] Set `AI_PROVIDER=openai` and provide `OPENAI_API_KEY` if using LLM
- [ ] Review the `data_retention_days` setting
- [ ] Evaluate a dedicated vector store only if production scale requires it

The accounts under `@demo.local` and their shared password are fictional,
public demo credentials. They are intentionally insecure and must never be
copied to a real environment.
