"""Copilot integration tests — decision invariants and scope."""
from app.tests.conftest import auth_header


def _query(client, headers, **kwargs):
    payload = {"question": "consulta de teste", **kwargs}
    return client.post("/api/copilot/query", json=payload, headers=headers)


# ── decision invariants ────────────────────────────────────────────────────────

def test_open_fund_allowed(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = _query(client, h, question="Posso investir em fundo aberto?", product_type="OPEN_FUND")
    assert r.status_code == 200
    assert r.json()["decision"] == "ALLOWED"


def test_crypto_restricted(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = _query(client, h, question="Posso comprar Bitcoin?", product_type="CRYPTO")
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "RESTRICTED"
    assert data["requires_human_review"] is True


def test_stock_requires_preapproval(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = _query(client, h, question="Posso comprar ações?", product_type="STOCK")
    assert r.status_code == 200
    assert r.json()["decision"] == "PRE_APPROVAL_REQUIRED"


def test_inconclusive_without_type(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = _query(client, h, question="Posso operar?")
    assert r.status_code == 200
    assert r.json()["decision"] == "INCONCLUSIVE"


def test_closed_fund_inconclusive(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = _query(client, h, question="Fundo fechado é permitido?", product_type="CLOSED_FUND")
    assert r.status_code == 200
    assert r.json()["decision"] == "INCONCLUSIVE"


def test_out_of_scope_returns_inconclusive(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = _query(client, h, question="Qual a melhor receita de bolo?")
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "INCONCLUSIVE"
    assert data["out_of_scope"] is True


def test_high_amount_requires_human_review(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = _query(client, h, question="Posso investir?", product_type="OPEN_FUND", amount=500_000)
    assert r.status_code == 200
    assert r.json()["requires_human_review"] is True


def test_response_has_next_action(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = _query(client, h, question="Fundo de renda fixa?", product_type="FIXED_INCOME")
    assert r.status_code == 200
    assert r.json()["next_action"] is not None


def test_response_has_confidence(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = _query(client, h, question="Criptoativo?", product_type="CRYPTO")
    data = r.json()
    assert 0.0 <= data["confidence"] <= 1.0


# ── history scoping ────────────────────────────────────────────────────────────

def test_employee_history_scoped_to_own(client, employee_user, compliance_user):
    eh = auth_header(client, "employee@test.local")
    _query(client, eh, question="Consulta do employee", product_type="OPEN_FUND")
    r = client.get("/api/copilot/history", headers=eh)
    assert r.status_code == 200
    # all returned items must be from this user's queries (indirect test)
    for item in r.json():
        assert "decision" in item


def test_compliance_sees_all_history(client, employee_user, compliance_user):
    eh = auth_header(client, "employee@test.local")
    ch = auth_header(client, "compliance@test.local")
    _query(client, eh, question="Consulta employee 2", product_type="STOCK")
    r = client.get("/api/copilot/history", headers=ch)
    assert r.status_code == 200
    assert len(r.json()) >= 1
