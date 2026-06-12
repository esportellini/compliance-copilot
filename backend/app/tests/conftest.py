"""Test fixtures.

Uses SQLite in-memory so no Postgres instance is needed for CI.
The JSONB/ARRAY dialect differences don't affect the business logic tests here.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.user import User

SQLITE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # import all models so metadata is populated
    import app.models.audit, app.models.copilot, app.models.document  # noqa: F401
    import app.models.pre_approval, app.models.product, app.models.restricted  # noqa: F401
    import app.models.rule, app.models.setting, app.models.training, app.models.user  # noqa: F401
    from app.db.base import Base
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture(scope="session")
def SessionTest(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db(SessionTest):
    session = SessionTest()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ── user fixtures ──────────────────────────────────────────────────────────────

def _make_user(db, email, role, full_name="Test User"):
    u = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password("Test1234!"),
        role=role,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def admin_user(db):
    return _make_user(db, "admin@test.local", "ADMIN", "Admin Test")


@pytest.fixture()
def compliance_user(db):
    return _make_user(db, "compliance@test.local", "COMPLIANCE", "Compliance Test")


@pytest.fixture()
def employee_user(db):
    return _make_user(db, "employee@test.local", "EMPLOYEE", "Employee Test")


@pytest.fixture()
def auditor_user(db):
    return _make_user(db, "auditor@test.local", "AUDITOR", "Auditor Test")


def auth_header(client, email: str, password: str = "Test1234!") -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
