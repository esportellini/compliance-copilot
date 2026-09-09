# LGPD and Privacy

## Legal Basis (Base Legal)

| Data Category           | Legal Basis          | Retention     |
|-------------------------|----------------------|---------------|
| User credentials        | Define per deployment | Administrative anonymization available |
| Copilot queries         | Define per deployment | No automated deletion in this version |
| Pre-approvals           | Define per deployment | No automated deletion in this version |
| Audit logs              | Define per deployment | Configurable cleanup with protected events |
| Training acknowledgements | Define per deployment | No automated deletion in this version |

The legal basis and retention period depend on the deploying organization and
must be approved by its privacy and legal teams. This demo does not determine
them.

## Data Subject Rights (Art. 18 LGPD)

| Right                  | Implementation                                    |
|------------------------|---------------------------------------------------|
| Access (Acesso)        | `GET /api/privacy/user-data/{id}` (Admin)         |
| Rectification          | `PATCH /api/users/{id}` (Admin)                   |
| Erasure / Anonymization| `POST /api/privacy/anonymize-user/{id}` (Admin)   |
| Portability            | JSON export via user-data endpoint                |
| Information            | `GET /api/privacy/info` (all users)               |

## Data Minimization

The system does not collect:
- IP addresses
- Location data
- Biometric data
- Health data
- Financial account numbers (only operation descriptions)
- Third-party personal data

## Retention Policy

Configured via `data_retention_days` setting (default: 730 days = 2 years).

Protected events that are **never** auto-deleted:
- `USER_ANONYMIZED`
- `PRE_APPROVAL_DECISION`
- `PRODUCT_BLOCKED`
- `PRODUCT_RESTRICTED`
- `USER_DEACTIVATED`
- `RETENTION_RUN`
- Any event with `severity = CRITICAL`

## AI and Data

- **No automatic external model training**: user queries are not sent to any
  external service without explicit `AI_PROVIDER=openai` configuration.
- **Mock provider (default)**: fully offline, no data leaves the system.
- **OpenAI provider**: query text and retrieved policy excerpts are sent to
  OpenAI API. Users should be informed per their privacy notice.
- Prompts are stored in `copilot_queries` for audit purposes. Automated query
  deletion is not implemented in this version; deployments need an approved
  retention procedure before production use.

## Anonymization Process

Anonymization replaces personal fields with non-identifiable values:
- `email` → `anonimizado_{id}@removido.local`
- `full_name` → `Usuário Anonimizado`
- `hashed_password` → `""` (login disabled)
- `department` → `null`

Audit logs referencing the user are preserved but contain no personal data
beyond what was already recorded at event time.
