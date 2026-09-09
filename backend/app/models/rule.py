from datetime import datetime, timezone
import re

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ComplianceRule(Base, TimestampMixin):
    __tablename__ = "compliance_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_key: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_type: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    condition: Mapped[dict] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), default=dict
    )
    decision: Mapped[str] = mapped_column(String(32))
    risk: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    priority: Mapped[int] = mapped_column(Integer, default=100)  # lower = evaluated first
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("rule_key", "version", name="uq_rule_key_version"),
        Index(
            "uq_active_rule_key", "rule_key", unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
            sqlite_where=text("status = 'ACTIVE'"),
        ),
    )

    def __init__(self, **kwargs):
        if not kwargs.get("rule_key"):
            key = re.sub(r"[^a-z0-9]+", "-", kwargs.get("name", "rule").lower()).strip("-")
            kwargs["rule_key"] = key or "rule"
        super().__init__(**kwargs)
