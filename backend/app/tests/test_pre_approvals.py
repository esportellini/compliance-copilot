"""Pre-approval tests."""
from app.tests.conftest import auth_header


def test_employee_can_create_pre_approval(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = client.post("/api/pre-approvals", json={
        "product_label": "Fundo Teste",
        "operation_type": "COMPRA",
        "estimated_amount": 50000,
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "PENDING"
    assert data["requester_id"] == employee_user.id


def test_employee_sees_own_pre_approvals_only(client, employee_user, compliance_user):
    eh = auth_header(client, "employee@test.local")
    ch = auth_header(client, "compliance@test.local")
    # create as employee
    client.post("/api/pre-approvals", json={"product_label": "P", "operation_type": "COMPRA"}, headers=eh)
    # employee list
    r_emp = client.get("/api/pre-approvals", headers=eh)
    assert r_emp.status_code == 200
    for item in r_emp.json():
        assert item["requester_id"] == employee_user.id


def test_compliance_can_update_status(client, employee_user, compliance_user):
    eh = auth_header(client, "employee@test.local")
    ch = auth_header(client, "compliance@test.local")
    r = client.post("/api/pre-approvals", json={"product_label": "X", "operation_type": "VENDA"}, headers=eh)
    req_id = r.json()["id"]
    client.patch(f"/api/pre-approvals/{req_id}/status",
                 json={"status": "IN_REVIEW"}, headers=ch)
    r2 = client.patch(f"/api/pre-approvals/{req_id}/status",
                      json={"status": "APPROVED", "compliance_opinion": "OK"}, headers=ch)
    assert r2.status_code == 200
    assert r2.json()["status"] == "APPROVED"


def test_employee_cannot_update_status(client, employee_user):
    eh = auth_header(client, "employee@test.local")
    r = client.post("/api/pre-approvals", json={"product_label": "Y", "operation_type": "COMPRA"}, headers=eh)
    req_id = r.json()["id"]
    r2 = client.patch(f"/api/pre-approvals/{req_id}/status",
                      json={"status": "APPROVED"}, headers=eh)
    assert r2.status_code == 403


def test_auditor_can_read_pre_approvals(client, auditor_user, employee_user):
    eh = auth_header(client, "employee@test.local")
    client.post("/api/pre-approvals", json={"product_label": "Z", "operation_type": "COMPRA"}, headers=eh)
    ah = auth_header(client, "auditor@test.local")
    r = client.get("/api/pre-approvals", headers=ah)
    assert r.status_code == 200


def test_cannot_reopen_terminal_pre_approval(client, employee_user, compliance_user):
    eh = auth_header(client, "employee@test.local")
    ch = auth_header(client, "compliance@test.local")
    r = client.post("/api/pre-approvals", json={"product_label": "W", "operation_type": "COMPRA"}, headers=eh)
    req_id = r.json()["id"]
    client.patch(f"/api/pre-approvals/{req_id}/status",
                 json={"status": "REJECTED", "compliance_opinion": "Negado."}, headers=ch)
    # try to re-open
    r3 = client.patch(f"/api/pre-approvals/{req_id}/status",
                      json={"status": "APPROVED"}, headers=ch)
    assert r3.status_code == 400
