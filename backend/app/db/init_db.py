"""Bootstrap the database schema.

This module is used by the seed script and by tests. In production, prefer
running Alembic migrations instead of create_all — but this fallback ensures
the schema is always up to date in development without manual steps.
"""
from app.db.base import Base
from app.db.session import engine

# ensure all models are registered on Base.metadata before create_all
import app.models.audit  # noqa: F401
import app.models.copilot  # noqa: F401
import app.models.document  # noqa: F401
import app.models.pre_approval  # noqa: F401
import app.models.product  # noqa: F401
import app.models.restricted  # noqa: F401
import app.models.rule  # noqa: F401
import app.models.setting  # noqa: F401
import app.models.training  # noqa: F401
import app.models.user  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
