from datetime import date, datetime

from pydantic import BaseModel, field_validator

from app.schemas.enums import DocumentStatus


class DocumentBase(BaseModel):
    name: str
    doc_type: str = "OTHER"
    version: str | None = None
    owner: str | None = None
    effective_date: date | None = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    name: str | None = None
    doc_type: str | None = None
    version: str | None = None
    owner: str | None = None
    effective_date: date | None = None
    status: DocumentStatus | None = None

    @field_validator("status")
    @classmethod
    def status_not_active_without_version(cls, v):
        # a validação completa (versão + responsável) acontece no endpoint
        return v


class DocumentOut(DocumentBase):
    id: int
    status: DocumentStatus
    original_filename: str | None = None
    file_size_bytes: int | None = None
    uploaded_at: datetime | None = None
    processed_at: datetime | None = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChunkOut(BaseModel):
    id: int
    chunk_index: int
    page_number: int | None = None
    section_title: str | None = None
    content: str
    char_count: int = 0

    model_config = {"from_attributes": True}
