from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ComplianceRule(Base, TimestampMixin):
    __tablename__ = "compliance_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_type: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    condition: Mapped[dict] = mapped_column(JSONB, default=dict)
    decision: Mapped[str] = mapped_column(String(32))
    risk: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    priority: Mapped[int] = mapped_column(Integer, default=100)  # lower = evaluated first
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
