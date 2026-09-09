"""Repository contracts for reproducible application bootstrap."""
from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
FRONTEND_ROOT = REPOSITORY_ROOT / "frontend"


def test_application_runtime_uses_alembic_as_its_only_schema_bootstrap():
    runtime_sources = [
        path
        for path in (BACKEND_ROOT / "app").rglob("*.py")
        if "tests" not in path.parts
    ]

    assert not (BACKEND_ROOT / "app" / "db" / "init_db.py").exists()
    for path in runtime_sources:
        assert "create_all" not in path.read_text(encoding="utf-8"), path
    assert "init_db" not in (BACKEND_ROOT / "app" / "seed.py").read_text(
        encoding="utf-8"
    )


def test_compose_migrates_before_start_and_keeps_seed_explicit():
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "alembic upgrade head" in compose
    assert "condition: service_healthy" in compose
    assert "--reload" not in compose
    assert "./backend:/app" not in compose
    assert "python -m app.seed" not in compose


def test_frontend_install_and_quality_commands_are_reproducible():
    package = json.loads((FRONTEND_ROOT / "package.json").read_text(encoding="utf-8"))
    dockerfile = (FRONTEND_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert (FRONTEND_ROOT / "package-lock.json").exists()
    assert package["scripts"]["typecheck"] == "tsc --noEmit"
    assert package["scripts"]["lint"] == "next lint"
    assert "npm ci" in dockerfile
    assert "npm install" not in dockerfile


def test_removed_rate_limit_settings_do_not_remain_as_dead_configuration():
    settings = Settings()

    assert not hasattr(settings, "login_rate_limit")
    assert not hasattr(settings, "copilot_rate_limit")


def test_backend_development_requirements_include_test_runner():
    requirements = (BACKEND_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")

    assert "-r requirements.txt" in requirements
    assert "pytest==" in requirements


def test_ci_runs_the_complete_backend_and_frontend_quality_gate():
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    for command in (
        "python -m pytest -q",
        "python -m compileall -q app alembic",
        "python -m pytest app/tests/test_alembic_schema.py -q",
        "npm ci",
        "npm run typecheck",
        "npm run lint",
        "npm run build",
        "docker compose config --quiet",
    ):
        assert command in workflow
