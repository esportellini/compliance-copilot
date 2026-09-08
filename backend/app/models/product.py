from sqlalchemy import JSON, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.identifiers import normalize_identifier, normalized_identifier_expression
from app.db.base import Base, TimestampMixin


class FinancialProduct(Base, TimestampMixin):
    __tablename__ = "financial_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    product_type: Mapped[str] = mapped_column(String(48), index=True)
    identifier: Mapped[str | None] = mapped_column(String(64), nullable=True)  # ticker / CNPJ
    issuer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manager: Mapped[str | None] = mapped_column(String(255), nullable=True)
    administrator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk: Mapped[str | None] = mapped_column(String(16), nullable=True)
    liquidity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ALLOWED", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(
        ARRAY(String).with_variant(JSON(), "sqlite"), default=list
    )
    __table_args__ = (
        Index(
            "uq_financial_products_identifier_normalized",
            normalized_identifier_expression(identifier),
            unique=True,
        ),
    )

    @validates("identifier")
    def _canonicalize_identifier(self, _key: str, value: str | None) -> str | None:
        return normalize_identifier(value)
