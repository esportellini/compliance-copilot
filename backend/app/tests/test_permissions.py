"""RBAC permission tests — each role boundary."""
from app.tests.conftest import auth_header


# ── product endpoints ──────────────────────────────────────────────────────────

def test_employee_cannot_create_product(client, employee_user, compliance_user):
    h = auth_header(client, "employee@test.local")
    r = client.post("/api/products", json={"name": "T", "product_type": "OPEN_FUND"}, headers=h)
    assert r.status_code == 403


def test_compliance_can_create_product(client, compliance_user):
    h = auth_header(client, "compliance@test.local")
    r = client.post("/api/products", json={"name": "Fundo Teste", "product_type": "OPEN_FUND"}, headers=h)
    assert r.status_code == 201


def test_auditor_cannot_create_product(client, auditor_user):
    h = auth_header(client, "auditor@test.local")
    r = client.post("/api/products", json={"name": "T", "product_type": "OPEN_FUND"}, headers=h)
    assert r.status_code == 403


def test_auditor_can_read_products(client, auditor_user, compliance_user):
    # create first as compliance
    ch = auth_header(client, "compliance@test.local")
    client.post("/api/products", json={"name": "Auditavel", "product_type": "STOCK"}, headers=ch)
    # auditor reads
    ah = auth_header(client, "auditor@test.local")
    r = client.get("/api/products", headers=ah)
    assert r.status_code == 200


# ── rules ──────────────────────────────────────────────────────────────────────

def test_employee_cannot_create_rule(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = client.post("/api/rules", json={
        "name": "R", "decision": "ALLOWED", "risk": "LOW", "priority": 100, "is_active": True
    }, headers=h)
    assert r.status_code == 403


def test_auditor_cannot_create_rule(client, auditor_user, compliance_user):
    ah = auth_header(client, "auditor@test.local")
    r = client.post("/api/rules", json={
        "name": "R", "decision": "ALLOWED", "risk": "LOW", "priority": 100, "is_active": True
    }, headers=ah)
    assert r.status_code == 403


# ── audit logs ─────────────────────────────────────────────────────────────────

def test_employee_cannot_access_audit_logs(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = client.get("/api/audit-logs", headers=h)
    assert r.status_code == 403


def test_auditor_can_access_audit_logs(client, auditor_user):
    h = auth_header(client, "auditor@test.local")
    r = client.get("/api/audit-logs", headers=h)
    assert r.status_code == 200


# ── users endpoint ──────────────────────────────────────────────────────────────

def test_employee_cannot_list_users(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = client.get("/api/users", headers=h)
    assert r.status_code == 403


def test_auditor_cannot_list_users(client, auditor_user):
    h = auth_header(client, "auditor@test.local")
    r = client.get("/api/users", headers=h)
    assert r.status_code == 403


def test_admin_can_list_users(client, admin_user):
    h = auth_header(client, "admin@test.local")
    r = client.get("/api/users", headers=h)
    assert r.status_code == 200


# ── user management ────────────────────────────────────────────────────────────

def test_deactivate_user(client, admin_user, employee_user):
    h = auth_header(client, "admin@test.local")
    r = client.patch(f"/api/users/{employee_user.id}/deactivate", headers=h)
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_admin_cannot_deactivate_self(client, admin_user):
    h = auth_header(client, "admin@test.local")
    r = client.patch(f"/api/users/{admin_user.id}/deactivate", headers=h)
    assert r.status_code == 400


def test_get_user_by_id(client, admin_user, employee_user):
    h = auth_header(client, "admin@test.local")
    r = client.get(f"/api/users/{employee_user.id}", headers=h)
    assert r.status_code == 200
    assert "hashed_password" not in r.json()


def test_unauthenticated_blocked(client):
    r = client.get("/api/products")
    assert r.status_code == 401
