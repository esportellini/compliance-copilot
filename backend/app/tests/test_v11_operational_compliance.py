from datetime import datetime, timedelta, timezone
from io import BytesIO

from pypdf import PdfReader

from app.models.audit import AuditLog
from app.models.copilot import CopilotAnswer, SourceReference
from app.models.notification import Notification
from app.models.pre_approval import PreApprovalRequest
from app.models.product import FinancialProduct
from app.models.restricted import RestrictedListItem
from app.models.rule import ComplianceRule
from app.models.setting import SystemSetting
from app.tests.conftest import auth_header


def _rule_payload(**overrides):
    payload = {
        "rule_key": "personal-stock-trading",
        "name": "Ações exigem pré-aprovação",
        "product_type": "STOCK",
        "condition": {},
        "decision": "PRE_APPROVAL_REQUIRED",
        "risk": "MEDIUM",
        "priority": 10,
        "status": "DRAFT",
        "effective_from": "2026-01-01T00:00:00Z",
    }
    payload.update(overrides)
    return payload


def _product(db, identifier="XPTO3"):
    row = FinancialProduct(
        name=f"Ações {identifier}", product_type="STOCK", identifier=identifier,
        status="ALLOWED",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _query(client, headers, product_id):
    response = client.post(
        "/api/copilot/query",
        json={
            "question": "Posso comprar este ativo?",
            "product_id": product_id,
            "amount": 20_000,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _request(client, headers, source_query_id):
    response = client.post(
        "/api/pre-approvals",
        json={"source_query_id": source_query_id, "operation_type": "COMPRA"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_published_rule_edit_creates_new_version_and_preserves_query_provenance(
    client, db, compliance_user, employee_user,
):
    compliance = auth_header(client, "compliance@test.local")
    employee = auth_header(client, "employee@test.local")
    created = client.post("/api/rules", json=_rule_payload(), headers=compliance)
    assert created.status_code == 201, created.text
    v1 = created.json()
    activated = client.post(f"/api/rules/{v1['id']}/activate", headers=compliance)
    assert activated.status_code == 200, activated.text
    product = _product(db)

    query = _query(client, employee, product.id)
    provenance = query["rule_provenance"]
    assert provenance == [{
        "rule_id": v1["id"],
        "rule_key": "personal-stock-trading",
        "version": 1,
        "name": "Ações exigem pré-aprovação",
        "priority": 10,
        "decision": "PRE_APPROVAL_REQUIRED",
        "condition": {},
    }]

    edited = client.patch(
        f"/api/rules/{v1['id']}",
        json={"description": "Nova redação publicada"},
        headers=compliance,
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["version"] == 2
    assert edited.json()["status"] == "ACTIVE"
    assert db.get(ComplianceRule, v1["id"]).status == "ARCHIVED"

    old_history = client.get(
        f"/api/copilot/history/{query['query_id']}", headers=employee
    ).json()
    assert old_history["answer"]["rule_provenance"] == provenance


def test_only_active_and_effective_rule_versions_are_evaluated(
    client, db, employee_user,
):
    now = datetime.now(timezone.utc)
    product = _product(db)
    db.add_all([
        ComplianceRule(
            rule_key="timed-stock", version=1, name="Vigente",
            product_type="STOCK", condition={}, decision="ALLOWED", risk="LOW",
            priority=5, status="ACTIVE", is_active=True,
            effective_from=now - timedelta(days=1), effective_to=now + timedelta(days=1),
        ),
        ComplianceRule(
            rule_key="future-stock", version=1, name="Futura",
            product_type="STOCK", condition={}, decision="RESTRICTED", risk="HIGH",
            priority=1, status="ACTIVE", is_active=True,
            effective_from=now + timedelta(days=1),
        ),
    ])
    db.commit()
    employee = auth_header(client, "employee@test.local")

    result = _query(client, employee, product.id)

    assert result["decision"] == "ALLOWED"
    assert [item["name"] for item in result["rule_provenance"]] == ["Vigente"]


def test_second_active_version_for_same_rule_is_rejected(client, compliance_user):
    headers = auth_header(client, "compliance@test.local")
    first = client.post("/api/rules", json=_rule_payload(status="ACTIVE"), headers=headers)
    assert first.status_code == 201
    conflict = client.post(
        "/api/rules", json=_rule_payload(name="Outra versão", status="ACTIVE"), headers=headers
    )
    assert conflict.status_code == 409


def test_restricted_csv_preview_apply_audit_and_export(
    client, db, compliance_user, auditor_user,
):
    compliance = auth_header(client, "compliance@test.local")
    auditor = auth_header(client, "auditor@test.local")
    db.add(RestrictedListItem(identifier="ACME3", name="Old", reason="Old", active=True))
    db.commit()
    csv_bytes = (
        "identifier,name,reason,active\n"
        " acme3 ,ACME S.A.,Conflito interno,true\n"
        "XYZ4,XYZ Holdings,Under review,false\n"
    ).encode()

    preview = client.post(
        "/api/restricted-list/import/preview",
        files={"file": ("restricted.csv", csv_bytes, "text/csv")},
        headers=compliance,
    )
    assert preview.status_code == 200, preview.text
    assert [row["action"] for row in preview.json()["rows"]] == ["UPDATE", "ADD"]

    applied = client.post(
        "/api/restricted-list/import/apply", json=preview.json(), headers=compliance
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["added"] == 1
    assert applied.json()["updated"] == 1
    assert db.query(RestrictedListItem).filter_by(identifier="ACME3").one().name == "ACME S.A."
    audit = db.query(AuditLog).filter_by(event_type="RESTRICTED_LIST_IMPORTED").one()
    assert audit.meta["filename"] == "restricted.csv"
    assert "raw_file" not in audit.meta

    exported = client.get("/api/restricted-list/export.csv", headers=auditor)
    assert exported.status_code == 200
    assert "identifier,name,reason,active" in exported.text
    assert "ACME3" in exported.text


def test_restricted_csv_rejects_normalized_duplicates_without_changes(
    client, db, compliance_user,
):
    headers = auth_header(client, "compliance@test.local")
    payload = (
        "identifier,name,reason,active\n"
        "ACME3,ACME,Reason,true\n"
        " acme3 ,Duplicate,Reason,true\n"
    ).encode()

    response = client.post(
        "/api/restricted-list/import/preview",
        files={"file": ("bad.csv", payload, "text/csv")},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["line"] == 3
    assert db.query(RestrictedListItem).count() == 0


def test_restricted_csv_rejects_invalid_header_and_employee_access(
    client, compliance_user, employee_user,
):
    compliance = auth_header(client, "compliance@test.local")
    employee = auth_header(client, "employee@test.local")
    invalid = client.post(
        "/api/restricted-list/import/preview",
        files={"file": ("bad.csv", b"identifier,name\nACME3,ACME\n", "text/csv")},
        headers=compliance,
    )
    assert invalid.status_code == 422
    assert client.get("/api/restricted-list", headers=employee).status_code == 403
    assert client.get("/api/restricted-list/export.csv", headers=employee).status_code == 403


def test_sla_due_at_is_snapshotted_and_queue_prioritizes_overdue(
    client, db, employee_user, compliance_user,
):
    db.add(SystemSetting(key="pre_approval_sla_hours", value="24"))
    product = _product(db)
    db.add(ComplianceRule(
        rule_key="stock", version=1, name="Stock approval", product_type="STOCK",
        condition={}, decision="PRE_APPROVAL_REQUIRED", risk="MEDIUM", priority=10,
        status="ACTIVE", is_active=True,
        effective_from=datetime.now(timezone.utc) - timedelta(days=1),
    ))
    db.commit()
    employee = auth_header(client, "employee@test.local")
    compliance = auth_header(client, "compliance@test.local")
    query = _query(client, employee, product.id)
    created = _request(client, employee, query["query_id"])
    due = datetime.fromisoformat(created["due_at"])
    made = datetime.fromisoformat(created["created_at"])
    assert due - made == timedelta(hours=24)
    assert created["sla_status"] == "ON_TIME"

    request = db.get(PreApprovalRequest, created["id"])
    request.due_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()
    queue = client.get("/api/pre-approvals?sla=OVERDUE", headers=compliance)
    assert queue.status_code == 200
    assert [item["id"] for item in queue.json()] == [created["id"]]
    assert queue.json()[0]["sla_status"] == "OVERDUE"
    dashboard = client.get("/api/dashboard", headers=compliance).json()
    assert dashboard["overdue_count"] == 1
    assert dashboard["needs_attention"][0]["id"] == created["id"]

    request.due_at = datetime.now(timezone.utc) + timedelta(hours=6)
    db.commit()
    due_soon = client.get("/api/pre-approvals?sla=DUE_SOON", headers=compliance).json()
    assert due_soon[0]["id"] == created["id"]
    request.status = "APPROVED"
    db.commit()
    completed = client.get("/api/pre-approvals?sla=COMPLETED", headers=compliance).json()
    assert completed[0]["id"] == created["id"]


def test_workflow_notifications_are_private_and_markable(
    client, db, employee_user, compliance_user, admin_user, auditor_user,
):
    product = _product(db)
    db.add(ComplianceRule(
        rule_key="stock", version=1, name="Stock approval", product_type="STOCK",
        condition={}, decision="PRE_APPROVAL_REQUIRED", risk="MEDIUM", priority=10,
        status="ACTIVE", is_active=True,
        effective_from=datetime.now(timezone.utc) - timedelta(days=1),
    ))
    db.commit()
    employee = auth_header(client, "employee@test.local")
    compliance = auth_header(client, "compliance@test.local")
    query = _query(client, employee, product.id)
    request = _request(client, employee, query["query_id"])

    own = client.get("/api/notifications", headers=compliance)
    assert own.status_code == 200
    assert own.json()["unread_count"] == 1
    notification_id = own.json()["items"][0]["id"]
    assert own.json()["items"][0]["entity_id"] == request["id"]
    assert client.patch(
        f"/api/notifications/{notification_id}/read", headers=employee
    ).status_code == 404
    assert client.patch(
        f"/api/notifications/{notification_id}/read", headers=compliance
    ).status_code == 200

    client.patch(
        f"/api/pre-approvals/{request['id']}/status",
        json={"status": "REJECTED", "compliance_opinion": "Fora da política"},
        headers=compliance,
    )
    employee_box = client.get("/api/notifications", headers=employee).json()
    assert any(item["type"] == "PRE_APPROVAL_DECIDED" for item in employee_box["items"])
    assert client.post("/api/notifications/read-all", headers=employee).json()["updated"] >= 1


def test_audit_package_json_pdf_and_authorization(
    client, db, employee_user, compliance_user,
):
    product = _product(db)
    db.add(ComplianceRule(
        rule_key="stock", version=1, name="Stock approval", product_type="STOCK",
        condition={}, decision="PRE_APPROVAL_REQUIRED", risk="MEDIUM", priority=10,
        status="ACTIVE", is_active=True,
        effective_from=datetime.now(timezone.utc) - timedelta(days=1),
    ))
    db.commit()
    employee = auth_header(client, "employee@test.local")
    compliance = auth_header(client, "compliance@test.local")
    query = _query(client, employee, product.id)
    request = _request(client, employee, query["query_id"])

    answer = db.query(CopilotAnswer).filter_by(query_id=query["query_id"]).one()
    db.add(SourceReference(
        answer_id=answer.id, document_name="Investment Policy", document_version="2.1",
        section_title="3. AÇÕES", page_number=2, excerpt="Operações exigem aprovação.", score=0.91,
    ))
    stored = db.get(PreApprovalRequest, request["id"])
    stored.status = "APPROVED"
    stored.reviewer = "compliance@test.local"
    stored.review_started_at = datetime.now(timezone.utc) - timedelta(hours=1)
    stored.compliance_opinion = "Aprovado conforme política interna."
    stored.decided_at = datetime.now(timezone.utc)
    db.commit()

    package = client.get(
        f"/api/pre-approvals/{request['id']}/audit-package.json", headers=employee
    )
    assert package.status_code == 200, package.text
    data = package.json()
    assert data["header"]["request_id"] == request["id"]
    assert data["request"]["identifier"] == "XPTO3"
    assert data["initial_analysis"]["rule_provenance"][0]["version"] == 1
    assert data["human_workflow"]["status"] == "APPROVED"
    assert data["human_workflow"]["final_opinion"] == "Aprovado conforme política interna."
    assert data["documentary_evidence"][0]["version"] == "2.1"
    assert data["audit_events"]
    assert "educational" in data["disclaimer"].lower()

    pdf = client.get(
        f"/api/pre-approvals/{request['id']}/audit-package.pdf", headers=compliance
    )
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    text = "".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf.content)).pages)
    assert "Compliance Copilot" in text
    assert "XPTO3" in text
    assert "PRE_APPROVAL_REQUIRED" in text
    assert "Aprovado conforme política interna" in text

    other = type(employee_user)(
        email="other@test.local", full_name="Other", hashed_password=employee_user.hashed_password,
        role="EMPLOYEE", is_active=True,
    )
    db.add(other)
    db.commit()
    other_headers = auth_header(client, "other@test.local")
    denied = client.get(
        f"/api/pre-approvals/{request['id']}/audit-package.json", headers=other_headers
    )
    assert denied.status_code == 403
