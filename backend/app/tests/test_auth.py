"""Auth tests — login, JWT, /me."""
from app.tests.conftest import auth_header


def test_login_success(client, admin_user):
    r = client.post("/api/auth/login", json={"email": "admin@test.local", "password": "Test1234!"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, admin_user):
    r = client.post("/api/auth/login", json={"email": "admin@test.local", "password": "wrong"})
    assert r.status_code == 401
    assert "Credenciais" in r.json()["detail"]


def test_login_unknown_email(client):
    r = client.post("/api/auth/login", json={"email": "nobody@test.local", "password": "x"})
    assert r.status_code == 401


def test_me_returns_current_user(client, admin_user):
    h = auth_header(client, "admin@test.local")
    r = client.get("/api/auth/me", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "admin@test.local"
    assert data["role"] == "ADMIN"
    assert "hashed_password" not in data


def test_me_without_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_invalid_token(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert r.status_code == 401


def test_inactive_user_cannot_login(client, db):
    from app.models.user import User
    from app.core.security import hash_password
    u = User(email="inactive@test.local", full_name="Inactive",
              hashed_password=hash_password("Test1234!"), role="EMPLOYEE", is_active=False)
    db.add(u); db.commit()
    r = client.post("/api/auth/login", json={"email": "inactive@test.local", "password": "Test1234!"})
    assert r.status_code == 401
