"""Privacy and LGPD tests."""
from app.tests.conftest import auth_header, _make_user


def test_export_user_data(client, admin_user, employee_user):
    h = auth_header(client, "admin@test.local")
    r = client.get(f"/api/privacy/user-data/{employee_user.id}", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "titular" in data
    assert "consultas_copilot" in data
    assert "totais" in data
    assert "hashed_password" not in str(data)


def test_export_generates_audit_log(client, db, admin_user, employee_user):
    from app.models.audit import AuditLog
    h = auth_header(client, "admin@test.local")
    client.get(f"/api/privacy/user-data/{employee_user.id}", headers=h)
    log = db.query(AuditLog).filter(AuditLog.event_type == "USER_DATA_EXPORTED").first()
    assert log is not None


def test_employee_cannot_export_data(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = client.get(f"/api/privacy/user-data/{employee_user.id}", headers=h)
    assert r.status_code == 403


def test_anonymize_requires_inactive_user(client, db, admin_user):
    u = _make_user(db, "active_anon@test.local", "EMPLOYEE")
    h = auth_header(client, "admin@test.local")
    r = client.post(f"/api/privacy/anonymize-user/{u.id}", headers=h)
    assert r.status_code == 400
    assert "desative" in r.json()["detail"].lower()


def test_anonymize_inactive_user(client, db, admin_user):
    u = _make_user(db, "inactive_anon@test.local", "EMPLOYEE")
    u.is_active = False
    db.commit()
    h = auth_header(client, "admin@test.local")
    r = client.post(f"/api/privacy/anonymize-user/{u.id}", headers=h)
    assert r.status_code == 200
    db.refresh(u)
    assert u.is_anonymized is True
    assert "anonimizado" in u.email


def test_anonymize_already_anonymized(client, db, admin_user):
    u = _make_user(db, "already_anon@test.local", "EMPLOYEE")
    u.is_active = False
    u.is_anonymized = True
    db.commit()
    h = auth_header(client, "admin@test.local")
    r = client.post(f"/api/privacy/anonymize-user/{u.id}", headers=h)
    assert r.status_code == 400


def test_admin_cannot_anonymize_self(client, admin_user):
    h = auth_header(client, "admin@test.local")
    r = client.post(f"/api/privacy/anonymize-user/{admin_user.id}", headers=h)
    assert r.status_code == 400


def test_retention_policy_runs(client, admin_user):
    h = auth_header(client, "admin@test.local")
    r = client.post("/api/privacy/run-retention-policy", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "deleted_audit_logs" in data
    assert "cutoff_date" in data
    assert "protected_events_preserved" in data


def test_privacy_info_public_to_all(client, employee_user):
    h = auth_header(client, "employee@test.local")
    r = client.get("/api/privacy/info", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["principios_lgpd"]) == 7
    assert len(data["minimizacao"]) > 0
