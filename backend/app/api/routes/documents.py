from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_compliance
from app.db.session import get_db
from app.models.document import DocumentChunk, PolicyDocument
from app.models.user import User
from app.schemas.document import ChunkOut, DocumentOut, DocumentUpdate
from app.services.audit import log_event
from app.services.extractor import ExtractedPage, extract_text
from app.services.rag import index_document_from_pages

router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
_MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


def _ext(filename: str) -> str:
    return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


@router.get("", response_model=list[DocumentOut])
def list_documents(
    status: str | None = Query(default=None),
    doc_type: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(PolicyDocument)
    if not include_archived and not status:
        q = q.filter(PolicyDocument.status != "ARCHIVED")
    if status:
        q = q.filter(PolicyDocument.status == status)
    if doc_type:
        q = q.filter(PolicyDocument.doc_type == doc_type)
    return q.order_by(PolicyDocument.created_at.desc()).all()


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    d = db.get(PolicyDocument, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return d


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    name: str = Form(...),
    doc_type: str = Form("OTHER"),
    version: str | None = Form(default=None),
    owner: str | None = Form(default=None),
    effective_date: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_compliance),
):
    ext = _ext(file.filename or "")
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado: {ext or 'desconhecido'}. Use PDF, DOCX ou TXT.",
        )

    raw = await file.read()
    if len(raw) > _MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo excede o limite de 20 MB.")
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    full_text, pages = extract_text(raw, file.filename or "arquivo.txt")

    eff_date = None
    if effective_date:
        from datetime import date
        try:
            eff_date = date.fromisoformat(effective_date)
        except ValueError:
            pass

    doc = PolicyDocument(
        name=name,
        doc_type=doc_type,
        version=version,
        owner=owner,
        effective_date=eff_date,
        extracted_text=full_text,
        original_filename=file.filename,
        file_size_bytes=len(raw),
        uploaded_at=datetime.now(timezone.utc),
        status="DRAFT",
    )
    db.add(doc)
    db.flush()
    index_document_from_pages(doc, pages, db)

    log_event(
        db, "DOCUMENT_UPLOADED",
        f"Documento enviado: {name} ({file.filename}, {len(raw):,} bytes)",
        user_id=actor.id, actor_label=actor.email,
        entity="policy_documents", entity_id=doc.id,
        meta={"filename": file.filename, "doc_type": doc_type, "pages": len(pages)},
    )
    db.commit()
    db.refresh(doc)
    return doc


@router.patch("/{doc_id}", response_model=DocumentOut)
def update_document(
    doc_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_compliance),
):
    d = db.get(PolicyDocument, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    changes = payload.model_dump(exclude_none=True)

    # regra: ativar requer versão e responsável
    if changes.get("status") == "ACTIVE":
        version = changes.get("version", d.version)
        owner = changes.get("owner", d.owner)
        if not version or not owner:
            raise HTTPException(
                status_code=400,
                detail="Documento precisa de versão e responsável para ser ativado.",
            )

    old_status = d.status
    for k, v in changes.items():
        setattr(d, k, v)

    new_status = changes.get("status", old_status)
    if new_status != old_status:
        log_event(
            db, "DOCUMENT_STATUS_CHANGED",
            f"Status do documento '{d.name}' alterado: {old_status} → {new_status}",
            user_id=actor.id, actor_label=actor.email,
            entity="policy_documents", entity_id=d.id,
            severity="INFO" if new_status != "ARCHIVED" else "WARNING",
        )
    else:
        log_event(
            db, "DOCUMENT_UPDATED",
            f"Documento atualizado: {d.name}",
            user_id=actor.id, actor_label=actor.email,
            entity="policy_documents", entity_id=d.id,
        )
    db.commit()
    db.refresh(d)
    return d


@router.post("/{doc_id}/process", response_model=DocumentOut)
def process_document(
    doc_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_compliance),
):
    """Indexa (ou re-indexa) os chunks e ativa o documento."""
    d = db.get(PolicyDocument, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if d.status == "ARCHIVED":
        raise HTTPException(status_code=400, detail="Documento arquivado não pode ser reprocessado.")
    if not d.extracted_text:
        raise HTTPException(status_code=400, detail="Documento sem texto extraído.")

    # para ativar é obrigatório versão e responsável
    if not d.version or not d.owner:
        raise HTTPException(
            status_code=400,
            detail="Defina versão e responsável antes de processar o documento.",
        )

    # Upload already indexed extractor output. Reuse those persisted chunks so
    # processing never loses PDF pages or DOCX/TXT section titles.
    existing_chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == d.id)
        .order_by(DocumentChunk.chunk_index, DocumentChunk.id)
        .all()
    )
    if existing_chunks:
        pages = [
            ExtractedPage(
                text=chunk.content,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
            )
            for chunk in existing_chunks
        ]
    else:
        _, pages = extract_text(d.extracted_text.encode("utf-8"), "documento.txt")
    n = index_document_from_pages(d, pages, db)
    d.status = "ACTIVE"
    d.processed_at = datetime.now(timezone.utc)

    log_event(
        db, "DOCUMENT_PROCESSED",
        f"Documento indexado: {d.name} — {n} chunks",
        user_id=actor.id, actor_label=actor.email,
        entity="policy_documents", entity_id=d.id,
        meta={"chunk_count": n},
    )
    db.commit()
    db.refresh(d)
    return d


@router.post("/{doc_id}/archive", response_model=DocumentOut)
def archive_document(
    doc_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_compliance),
):
    d = db.get(PolicyDocument, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if d.status == "ARCHIVED":
        raise HTTPException(status_code=400, detail="Documento já está arquivado.")
    d.status = "ARCHIVED"
    log_event(
        db, "DOCUMENT_ARCHIVED",
        f"Documento arquivado: {d.name}",
        user_id=actor.id, actor_label=actor.email,
        entity="policy_documents", entity_id=d.id,
        severity="WARNING",
    )
    db.commit()
    db.refresh(d)
    return d


@router.get("/{doc_id}/chunks", response_model=list[ChunkOut])
def list_chunks(
    doc_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    d = db.get(PolicyDocument, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return sorted(d.chunks, key=lambda c: c.chunk_index)
