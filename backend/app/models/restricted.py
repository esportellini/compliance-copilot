from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.identifiers import normalize_identifier, normalized_identifier_expression
from app.db.base import Base, TimestampMixin


class RestrictedListItem(Base, TimestampMixin):
    __tablename__ = "restricted_list_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(String(64), index=True)  # ticker / CNPJ / token
    name: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    __table_args__ = (
        Index(
            "uq_restricted_list_identifier_normalized",
            normalized_identifier_expression(identifier),
            unique=True,
        ),
    )

    @validates("identifier")
    def _canonicalize_identifier(self, _key: str, value: str) -> str:
        normalized = normalize_identifier(value)
        if normalized is None:
            raise ValueError("identifier não pode ser vazio")
        return normalized
