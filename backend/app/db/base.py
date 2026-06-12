"""Declarative base + import surface for Alembic autogenerate.

Importing the models here ensures they're registered on the metadata before
migrations run.
"""
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# noqa: E402,F401 — imported for metadata registration / Alembic autogenerate
from app.models import (  # noqa: E402,F401
    user,
    document,
    product,
    rule,
    copilot,
    pre_approval,
    audit,
    setting,
    training,
    restricted,
)
