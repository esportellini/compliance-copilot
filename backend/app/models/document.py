from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# tipos de documento reconhecidos pela interface
DOCUMENT_TYPES = [
    ("INVESTMENT_POLICY",  "Política de investimentos pessoais"),
    ("ETHICS_CODE",        "Código de ética"),
    ("COMPLIANCE_MANUAL",  "Manual de compliance"),
    ("SUITABILITY_POLICY", "Política de suitability"),
    ("CONFLICT_POLICY",    "Política de conflitos de interesse"),
    ("RESTRICTED_LIST",    "Lista restrita"),
    ("WATCH_LIST",         "Lista de observação"),
    ("INTERNAL_MEMO",      "Comunicados internos"),
    ("OPERATIONAL_PROC",   "Procedimentos operacionais"),
    ("OTHER",              "Outro"),
]


class PolicyDocument(Base, TimestampMixin):
    __tablename__ = "policy_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    doc_type: Mapped[str] = mapped_column(String(64), default="OTHER", index=True)
    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # texto extraído — não é o arquivo original, apenas o conteúdo textual
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    chunks = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("policy_documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    # metadata de localização — preenchido quando disponível (PDF: página; DOCX: heading)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    # embedding como JSON list de floats; swap para pgvector.Vector em produção
    embedding: Mapped[list | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    char_count: Mapped[int] = mapped_column(Integer, default=0)

    document = relationship("PolicyDocument", back_populates="chunks")
