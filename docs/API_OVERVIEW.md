# API Overview

Base URL: `http://localhost:8000/api`
Interactive docs: `http://localhost:8000/docs` (local only)

## Authentication

All endpoints (except `/health` and `/api/auth/login`) require:
```
Authorization: Bearer <access_token>
```

## Endpoints

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Login with email + password |
| GET | `/auth/me` | Current user info |

### Copilot
| Method | Path | Description |
|--------|------|-------------|
| POST | `/copilot/query` | Submit a compliance query |
| GET | `/copilot/history` | List queries (scoped by role) |
| GET | `/copilot/history/{id}` | Query detail with sources |

### Products
| Method | Path | Description |
|--------|------|-------------|
| GET | `/products` | List (filterable by type/status/risk) |
| POST | `/products` | Create (compliance+) |
| GET | `/products/{id}` | Detail |
| PATCH | `/products/{id}` | Update (compliance+) |
| PATCH | `/products/{id}/restrict` | Mark as restricted (compliance+) |
| PATCH | `/products/{id}/block` | Mark as blocked (compliance+) |
| DELETE | `/products/{id}` | Delete (compliance+) |
| GET | `/products/{id}/queries` | Related Copilot queries |

### Rules
| Method | Path | Description |
|--------|------|-------------|
| GET | `/rules` | List all rules |
| POST | `/rules` | Create rule (compliance+) |
| PATCH | `/rules/{id}` | Update rule (compliance+) |
| DELETE | `/rules/{id}` | Delete rule (compliance+) |
| POST | `/rules/evaluate` | Simulate evaluation (any role) |

### Documents
| Method | Path | Description |
|--------|------|-------------|
| GET | `/documents` | List (filter by status/type) |
| POST | `/documents/upload` | Upload PDF/DOCX/TXT (compliance+) |
| GET | `/documents/{id}` | Detail |
| PATCH | `/documents/{id}` | Update metadata (compliance+) |
| POST | `/documents/{id}/process` | Index chunks + activate (compliance+) |
| POST | `/documents/{id}/archive` | Archive (compliance+) |
| GET | `/documents/{id}/chunks` | List chunks |

### Pre-approvals
| Method | Path | Description |
|--------|------|-------------|
| GET | `/pre-approvals` | List (scoped by role) |
| POST | `/pre-approvals` | Create (any role) |
| GET | `/pre-approvals/{id}` | Detail |
| PATCH | `/pre-approvals/{id}/status` | Update status (compliance+) |
| POST | `/pre-approvals/{id}/comments` | Add comment |

### Audit & Reports
| Method | Path | Description |
|--------|------|-------------|
| GET | `/audit-logs` | List events (compliance/auditor/admin) |
| GET | `/audit-logs/export/csv` | Download CSV |
| GET | `/reports/summary` | Aggregated metrics |
| GET | `/reports/top-products` | Most queried product types |
| GET | `/reports/pre-approvals-by-status` | PA distribution |
| GET | `/reports/top-documents` | Most cited documents |
| GET | `/reports/top-rules` | Most applied rules |
| GET | `/reports/export/csv` | Download query report |

### Privacy
| Method | Path | Description |
|--------|------|-------------|
| GET | `/privacy/info` | LGPD inventory (all users) |
| GET | `/privacy/user-data/{id}` | Export user data (admin) |
| POST | `/privacy/anonymize-user/{id}` | Anonymize user (admin) |
| POST | `/privacy/run-retention-policy` | Run retention (admin) |

### Admin
| Method | Path | Description |
|--------|------|-------------|
| GET | `/users` | List users (admin) |
| POST | `/users` | Create user (admin) |
| GET | `/users/{id}` | User detail (admin) |
| PATCH | `/users/{id}` | Update user (admin) |
| PATCH | `/users/{id}/deactivate` | Deactivate (admin) |
| GET | `/settings` | List settings (compliance+) |
| PUT | `/settings/{key}` | Update setting (admin) |
| GET | `/dashboard` | Dashboard metrics |
| GET | `/training` | Training items |
| POST | `/training/acknowledge` | Mark item read |
