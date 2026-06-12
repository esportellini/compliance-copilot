from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class CopilotQuery(Base, TimestampMixin):
    __tablename__ = "copilot_queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    product_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("financial_products.id"), nullable=True
    )
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="queries")
    answer = relationship(
        "CopilotAnswer", back_populates="query", uselist=False, cascade="all, delete-orphan"
    )


class CopilotAnswer(Base, TimestampMixin):
    __tablename__ = "copilot_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(
        ForeignKey("copilot_queries.id", ondelete="CASCADE"), index=True
    )
    decision: Mapped[str] = mapped_column(String(32), index=True)
    answer: Mapped[str] = mapped_column(Text)
    justification: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    matched_rules: Mapped[list | None] = mapped_column(JSONB, default=list)

    query = relationship("CopilotQuery", back_populates="answer")
    sources = relationship(
        "SourceReference", back_populates="answer", cascade="all, delete-orphan"
    )


class SourceReference(Base, TimestampMixin):
    __tablename__ = "source_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_id: Mapped[int] = mapped_column(
        ForeignKey("copilot_answers.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("policy_documents.id"), nullable=True
    )
    chunk_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_name: Mapped[str] = mapped_column(String(255))
    excerpt: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float, default=0.0)

    answer = relationship("CopilotAnswer", back_populates="sources")
