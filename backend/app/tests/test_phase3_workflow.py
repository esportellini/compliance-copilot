"""End-to-end coverage for the compliance approval workflow."""
from __future__ import annotations

from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.copilot import CopilotAnswer, CopilotQuery
from app.models.pre_approval import PreApprovalRequest
from app.models.training import TrainingItem
from app.models.user import User
from app.seed import seed
from app.tests.conftest import auth_header


def _second_employee(db, email: str = "employee.b@test.local") -> User:
    user = User(
        email=email,
        full_name="Employee B",
        hashed_password=hash_password("Test1234!"),
        role="EMPLOYEE",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_request(client, headers, **overrides):
    payload = {"product_label": "XPTO3", "operation_type": "COMPRA"}
    payload.update(overrides)
    return client.post("/api/pre-approvals", json=payload, headers=headers)


def test_demo_users_authenticate_and_employee_completes_approval_happy_path(client, db):
    seed(db)
    for email in (
        "admin@demo.local",
        "compliance@demo.local",
        "colaborador@demo.local",
        "auditor@demo.local",
    ):
        login = client.post(
            "/api/auth/login",
            json={"email": email, "password": "Compliance123!"},
        )
        assert login.status_code == 200, email

    employee = auth_header(client, "colaborador@demo.local", "Compliance123!")
    compliance = auth_header(client, "compliance@demo.local", "Compliance123!")
    query = client.post(
        "/api/copilot/query",
        json={
            "question": "Posso comprar ações XPTO3?",
            "product_name_hint": "XPTO3",
            "amount": 25_000,
            "objective": "Diversificação da carteira pessoal",
        },
        headers=employee,
    )
    assert query.status_code == 200
    assert query.json()["decision"] == "PRE_APPROVAL_REQUIRED"
    query_id = query.json()["query_id"]
    history_detail = client.get(
        f"/api/copilot/history/{query_id}", headers=employee
    )
    assert history_detail.status_code == 200
    assert history_detail.json()["product_identifier"] == "XPTO3"
    assert "XPTO3" in history_detail.json()["product_label"]
    query_count = db.query(CopilotQuery).count()

    created = _create_request(
        client,
        employee,
        source_query_id=query_id,
        estimated_amount=None,
        justification=None,
    )

    assert created.status_code == 201
    request = created.json()
    request_id = request["id"]
    assert db.query(CopilotQuery).count() == query_count
    assert request["source_query_id"] == query_id
    assert request["copilot_initial_decision"] == "PRE_APPROVAL_REQUIRED"
    assert "PRE_APPROVAL_REQUIRED" in request["copilot_initial_response"]
    assert request["product_id"] is not None
    assert "XPTO3" in request["product_label"]
    assert request["estimated_amount"] == 25_000

    compliance_list = client.get("/api/pre-approvals", headers=compliance)
    assert request_id in [item["id"] for item in compliance_list.json()]

    comment = client.post(
        f"/api/pre-approvals/{request_id}/comments",
        json={"body": "Documentação conferida."},
        headers=compliance,
    )
    assert comment.status_code == 201

    review = client.patch(
        f"/api/pre-approvals/{request_id}/status",
        json={"status": "IN_REVIEW"},
        headers=compliance,
    )
    assert review.status_code == 200
    assert review.json()["review_started_at"] is not None
    assert review.json()["decided_at"] is None

    approved = client.patch(
        f"/api/pre-approvals/{request_id}/status",
        json={"status": "APPROVED", "compliance_opinion": "Operação aprovada."},
        headers=compliance,
    )
    assert approved.status_code == 200
    assert approved.json()["decided_at"] is not None

    employee_detail = client.get(
        f"/api/pre-approvals/{request_id}", headers=employee
    )
    assert employee_detail.status_code == 200
    assert employee_detail.json()["status"] == "APPROVED"
    assert employee_detail.json()["compliance_opinion"] == "Operação aprovada."
    assert employee_detail.json()["comments"][0]["body"] == "Documentação conferida."

    events = {
        row.event_type
        for row in db.query(AuditLog)
        .filter(
            AuditLog.entity == "pre_approval_requests",
            AuditLog.entity_id == request_id,
        )
        .all()
    }
    assert {
        "PRE_APPROVAL_CREATED",
        "PRE_APPROVAL_COMMENT",
        "PRE_APPROVAL_REVIEW_STARTED",
        "PRE_APPROVAL_DECISION",
    } <= events
    created_event = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type == "PRE_APPROVAL_CREATED",
            AuditLog.entity_id == request_id,
        )
        .one()
    )
    assert created_event.meta["source_query_id"] == query_id
    assert created_event.meta["product_label"] == request["product_label"]


def test_source_query_must_exist_and_belong_to_employee(
    client, db, employee_user
):
    other = _second_employee(db)
    other_headers = auth_header(client, other.email)
    query = client.post(
        "/api/copilot/query",
        json={"question": "Posso comprar ações?", "product_type": "STOCK"},
        headers=other_headers,
    )
    employee_headers = auth_header(client, employee_user.email)

    missing = _create_request(client, employee_headers, source_query_id=999_999)
    foreign = _create_request(
        client, employee_headers, source_query_id=query.json()["query_id"]
    )

    assert missing.status_code == 404
    assert "consulta" in missing.json()["detail"].lower()
    assert foreign.status_code == 403


def test_linked_request_keeps_snapshots_when_product_changes(
    client, db, employee_user
):
    from app.models.product import FinancialProduct
    from app.models.rule import ComplianceRule

    product = FinancialProduct(
        name="Ações XPTO",
        identifier="XPTO3",
        product_type="STOCK",
        status="ALLOWED",
    )
    db.add(product)
    db.add(
        ComplianceRule(
            name="Ações exigem pré-aprovação",
            product_type="STOCK",
            decision="PRE_APPROVAL_REQUIRED",
            risk="MEDIUM",
            priority=10,
            condition={},
            is_active=True,
        )
    )
    db.commit()
    headers = auth_header(client, employee_user.email)
    query = client.post(
        "/api/copilot/query",
        json={"question": "Posso comprar XPTO3?", "product_name_hint": "XPTO3"},
        headers=headers,
    ).json()
    created = _create_request(
        client, headers, source_query_id=query["query_id"]
    ).json()

    product.name = "Nome alterado posteriormente"
    product.identifier = "NOVO3"
    db.commit()
    detail = client.get(f"/api/pre-approvals/{created['id']}", headers=headers)

    assert "XPTO3" in detail.json()["product_label"]
    assert detail.json()["copilot_initial_decision"] == "PRE_APPROVAL_REQUIRED"


def test_deleting_source_query_nulls_link_and_keeps_request_snapshots(
    client, db, employee_user
):
    headers = auth_header(client, employee_user.email)
    query = CopilotQuery(user_id=employee_user.id, question="Consulta rastreável")
    db.add(query)
    db.flush()
    db.add(
        CopilotAnswer(
            query_id=query.id,
            decision="PRE_APPROVAL_REQUIRED",
            answer="Análise original",
            justification="Regra aplicável",
            risk_level="MEDIUM",
            confidence=1,
            requires_human_review=True,
            matched_rules=["R1"],
        )
    )
    db.commit()
    request = _create_request(client, headers, source_query_id=query.id).json()

    db.delete(query)
    db.commit()
    db.expire_all()
    persisted = db.get(PreApprovalRequest, request["id"])

    assert persisted.source_query_id is None
    assert persisted.copilot_initial_decision == "PRE_APPROVAL_REQUIRED"
    assert persisted.copilot_initial_response == "Análise original"


def test_unlinked_request_rejects_a_missing_product(client, employee_user):
    employee = auth_header(client, employee_user.email)

    response = _create_request(client, employee, product_id=999_999)

    assert response.status_code == 404
    assert "produto" in response.json()["detail"].lower()


def test_state_machine_and_required_opinions(client, employee_user, compliance_user):
    employee = auth_header(client, employee_user.email)
    compliance = auth_header(client, compliance_user.email)
    request_id = _create_request(client, employee).json()["id"]

    direct_approval = client.patch(
        f"/api/pre-approvals/{request_id}/status",
        json={"status": "APPROVED", "compliance_opinion": "OK"},
        headers=compliance,
    )
    assert direct_approval.status_code == 400

    review = client.patch(
        f"/api/pre-approvals/{request_id}/status",
        json={"status": "IN_REVIEW"},
        headers=compliance,
    )
    assert review.status_code == 200

    for status in ("APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED"):
        missing_opinion = client.patch(
            f"/api/pre-approvals/{request_id}/status",
            json={"status": status, "compliance_opinion": "   "},
            headers=compliance,
        )
        assert missing_opinion.status_code == 400, status

    conditions = client.patch(
        f"/api/pre-approvals/{request_id}/status",
        json={
            "status": "APPROVED_WITH_CONDITIONS",
            "compliance_opinion": "Limite máximo de R$ 25.000.",
        },
        headers=compliance,
    )
    assert conditions.status_code == 200
    assert conditions.json()["decided_at"] is not None

    terminal_change = client.patch(
        f"/api/pre-approvals/{request_id}/status",
        json={"status": "REJECTED", "compliance_opinion": "Alteração tardia."},
        headers=compliance,
    )
    assert terminal_change.status_code == 400


def test_employee_and_compliance_cancellation_rules(
    client, db, employee_user, compliance_user
):
    other = _second_employee(db)
    employee = auth_header(client, employee_user.email)
    other_headers = auth_header(client, other.email)
    compliance = auth_header(client, compliance_user.email)

    own_id = _create_request(client, employee).json()["id"]
    own_cancel = client.patch(
        f"/api/pre-approvals/{own_id}/status",
        json={"status": "CANCELLED"},
        headers=employee,
    )
    assert own_cancel.status_code == 200

    other_id = _create_request(client, other_headers).json()["id"]
    foreign_cancel = client.patch(
        f"/api/pre-approvals/{other_id}/status",
        json={"status": "CANCELLED"},
        headers=employee,
    )
    assert foreign_cancel.status_code == 403

    review = client.patch(
        f"/api/pre-approvals/{other_id}/status",
        json={"status": "IN_REVIEW"},
        headers=compliance,
    )
    assert review.status_code == 200
    compliance_cancel = client.patch(
        f"/api/pre-approvals/{other_id}/status",
        json={"status": "CANCELLED"},
        headers=compliance,
    )
    assert compliance_cancel.status_code == 200


def test_employee_cannot_cancel_after_review_started(
    client, employee_user, compliance_user
):
    employee = auth_header(client, employee_user.email)
    compliance = auth_header(client, compliance_user.email)
    request_id = _create_request(client, employee).json()["id"]
    client.patch(
        f"/api/pre-approvals/{request_id}/status",
        json={"status": "IN_REVIEW"},
        headers=compliance,
    )

    response = client.patch(
        f"/api/pre-approvals/{request_id}/status",
        json={"status": "CANCELLED"},
        headers=employee,
    )

    assert response.status_code == 403


def test_auditor_is_read_only_for_workflow_mutations(
    client, db, employee_user, auditor_user
):
    employee = auth_header(client, employee_user.email)
    auditor = auth_header(client, auditor_user.email)
    request_id = _create_request(client, employee).json()["id"]
    training = TrainingItem(title="Treinamento", body="Conteúdo")
    db.add(training)
    db.commit()

    responses = [
        client.post(
            "/api/copilot/query",
            json={"question": "Posso comprar ações?", "product_type": "STOCK"},
            headers=auditor,
        ),
        _create_request(client, auditor),
        client.post(
            f"/api/pre-approvals/{request_id}/comments",
            json={"body": "Comentário do auditor"},
            headers=auditor,
        ),
        client.patch(
            f"/api/pre-approvals/{request_id}/status",
            json={"status": "CANCELLED"},
            headers=auditor,
        ),
        client.post(
            "/api/training/acknowledge",
            json={"training_item_id": training.id},
            headers=auditor,
        ),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403, 403]
    assert client.get(f"/api/pre-approvals/{request_id}", headers=auditor).status_code == 200


def test_comment_must_contain_non_whitespace_text(client, employee_user):
    employee = auth_header(client, employee_user.email)
    request_id = _create_request(client, employee).json()["id"]

    response = client.post(
        f"/api/pre-approvals/{request_id}/comments",
        json={"body": "   "},
        headers=employee,
    )

    assert response.status_code == 422


def test_second_employee_cannot_see_first_employee_request(
    client, db, employee_user
):
    other = _second_employee(db)
    employee = auth_header(client, employee_user.email)
    other_headers = auth_header(client, other.email)
    request_id = _create_request(client, employee).json()["id"]

    assert client.get(
        f"/api/pre-approvals/{request_id}", headers=other_headers
    ).status_code == 403
    assert request_id not in [
        item["id"]
        for item in client.get("/api/pre-approvals", headers=other_headers).json()
    ]


def test_employee_dashboard_scopes_queries_decisions_pending_and_recent_activity(
    client, db, employee_user
):
    other = _second_employee(db)
    first_query = CopilotQuery(user_id=employee_user.id, question="Consulta própria")
    second_query = CopilotQuery(user_id=other.id, question="Consulta confidencial B")
    db.add_all([first_query, second_query])
    db.flush()
    db.add_all(
        [
            CopilotAnswer(
                query_id=first_query.id,
                decision="ALLOWED",
                answer="A",
                justification="A",
                risk_level="LOW",
                confidence=1,
                requires_human_review=False,
                matched_rules=[],
            ),
            CopilotAnswer(
                query_id=second_query.id,
                decision="RESTRICTED",
                answer="B",
                justification="B",
                risk_level="HIGH",
                confidence=1,
                requires_human_review=False,
                matched_rules=[],
            ),
            PreApprovalRequest(
                requester_id=employee_user.id,
                product_label="A",
                operation_type="COMPRA",
                status="PENDING",
            ),
            PreApprovalRequest(
                requester_id=other.id,
                product_label="B",
                operation_type="COMPRA",
                status="PENDING",
            ),
        ]
    )
    db.commit()
    headers = auth_header(client, employee_user.email)

    response = client.get("/api/dashboard", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["queries_this_month"] == 1
    assert data["by_decision"] == {"ALLOWED": 1}
    assert data["pending_approvals"] == 1
    assert [item["question"] for item in data["recent_queries"]] == [
        "Consulta própria"
    ]
    assert sum(item["count"] for item in data["queries_by_day"]) == 1
