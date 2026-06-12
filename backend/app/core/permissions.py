"""Role definitions and route-level access control.

Roles intentionally map to the four compliance personas. The matrix below is the
single source of truth for "can role X touch resource Y" so we don't scatter
inline checks across the routers.
"""
from enum import Enum


class Role(str, Enum):
    ADMIN = "ADMIN"
    COMPLIANCE = "COMPLIANCE"
    EMPLOYEE = "EMPLOYEE"
    AUDITOR = "AUDITOR"


# resources used by the access matrix
READ = "read"
WRITE = "write"

# what each role is allowed to do, per resource group.
# "own" means the employee can only see rows they created.
_MATRIX: dict[Role, dict[str, set[str]]] = {
    Role.ADMIN: {
        "users": {READ, WRITE},
        "products": {READ, WRITE},
        "documents": {READ, WRITE},
        "rules": {READ, WRITE},
        "copilot": {READ, WRITE},
        "pre_approvals": {READ, WRITE},
        "audit": {READ},
        "training": {READ, WRITE},
        "privacy": {READ, WRITE},
        "settings": {READ, WRITE},
    },
    Role.COMPLIANCE: {
        "users": {READ},
        "products": {READ, WRITE},
        "documents": {READ, WRITE},
        "rules": {READ, WRITE},
        "copilot": {READ, WRITE},
        "pre_approvals": {READ, WRITE},
        "audit": {READ},
        "training": {READ},
        "settings": {READ},
    },
    Role.EMPLOYEE: {
        "products": {READ},
        "copilot": {READ, WRITE},  # scoped to own queries
        "pre_approvals": {READ, WRITE},  # scoped to own requests
        "training": {READ, WRITE},  # can acknowledge
        "documents": {READ},
    },
    Role.AUDITOR: {
        "users": {READ},
        "products": {READ},
        "documents": {READ},
        "rules": {READ},
        "copilot": {READ},
        "pre_approvals": {READ},
        "audit": {READ},
        "training": {READ},
        "settings": {READ},
    },
}


def can(role: Role, resource: str, action: str) -> bool:
    return action in _MATRIX.get(role, {}).get(resource, set())


def is_scoped_to_own(role: Role) -> bool:
    """Employees only ever see their own copilot queries / pre-approvals."""
    return role == Role.EMPLOYEE
