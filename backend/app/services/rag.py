"""Retrieval-Augmented Generation — chunking, indexação e busca.

Arquitetura:
  1. Extrator  →  lista de ExtractedPage (text + metadata de página/seção)
  2. Chunker   →  divide cada página em blocos de ≤ MAX_CHUNK_CHARS
  3. Embedder  →  vetor float[] via AIProvider (mock offline ou OpenAI)
  4. Retrieval →  cosine similarity + lexical overlap, ignorando docs ARCHIVED

Sem chave de IA: o MockAIProvider gera embeddings determinísticos por hash.
Para pgvector: troque o campo `embedding` (JSONB) por `pgvector.Vector(1536)`
e adicione um índice ivfflat — a query de busca muda para operador `<=>`.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.document import DocumentChunk, PolicyDocument
from app.services.ai_provider import get_provider
from app.services.extractor import ExtractedPage, extract_text

MAX_CHUNK_CHARS = 700
TOP_K = 4
EMBED_WEIGHT = 0.7
LEXICAL_WEIGHT = 0.3


# ─── chunking ─────────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    content: str
    page_number: int | None = None
    section_title: str | None = None


def _split_page(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Divide um bloco de texto em pedaços respeitando parágrafos e sentenças."""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 1 <= max_chars:
            current = (current + "\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            if len(para) > max_chars:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                buf = ""
                for sent in sentences:
                    if len(buf) + len(sent) + 1 <= max_chars:
                        buf = (buf + " " + sent).strip()
                    else:
                        if buf:
                            chunks.append(buf)
                        buf = sent[:max_chars]
                current = buf
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks or [text[:max_chars]]


def chunk_pages(pages: list[ExtractedPage]) -> list[Chunk]:
    result: list[Chunk] = []
    for page in pages:
        for text in _split_page(page.text):
            result.append(Chunk(
                content=text,
                page_number=page.page_number,
                section_title=page.section_title,
            ))
    return result


# ─── math helpers ─────────────────────────────────────────────────────────────

def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (norm_a * norm_b)


def _lexical(query: str, text: str) -> float:
    q_tokens = set(re.findall(r"\w+", query.lower()))
    t_tokens = set(re.findall(r"\w+", text.lower()))
    return len(q_tokens & t_tokens) / len(q_tokens) if q_tokens else 0.0


# ─── indexação ────────────────────────────────────────────────────────────────

def index_document(doc: PolicyDocument, db: Session) -> int:
    """(Re-)indexa todos os chunks de um documento.
    Deleta os chunks anteriores antes de criar novos.
    Retorna o número de chunks criados.
    """
    if not doc.extracted_text:
        return 0
    provider = get_provider()

    # apaga chunks anteriores
    for old in list(doc.chunks):
        db.delete(old)
    db.flush()

    # extrai com metadata (usa extractor se tiver filename, caso contrário só o texto)
    from app.services.extractor import _extract_txt
    if doc.original_filename:
        # já foi extraído no upload; reusa extracted_text mas tenta recuperar metadata
        # via extrator simulado a partir do texto puro
        _, pages = _extract_txt(doc.extracted_text.encode())
    else:
        _, pages = _extract_txt(doc.extracted_text.encode())

    chunks = chunk_pages(pages)
    for i, chunk in enumerate(chunks):
        try:
            embedding = provider.embed(chunk.content)
        except Exception:
            embedding = None
        db.add(DocumentChunk(
            document_id=doc.id,
            chunk_index=i,
            content=chunk.content,
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            embedding=embedding,
            char_count=len(chunk.content),
        ))

    doc.chunk_count = len(chunks)
    return len(chunks)


def index_document_from_pages(
    doc: PolicyDocument, pages: list[ExtractedPage], db: Session
) -> int:
    """Versão que recebe as páginas já extraídas (preserva metadata de PDF/DOCX)."""
    provider = get_provider()
    for old in list(doc.chunks):
        db.delete(old)
    db.flush()

    chunks = chunk_pages(pages)
    for i, chunk in enumerate(chunks):
        try:
            embedding = provider.embed(chunk.content)
        except Exception:
            embedding = None
        db.add(DocumentChunk(
            document_id=doc.id,
            chunk_index=i,
            content=chunk.content,
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            embedding=embedding,
            char_count=len(chunk.content),
        ))

    doc.chunk_count = len(chunks)
    return len(chunks)


# ─── busca / retrieval ────────────────────────────────────────────────────────

@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    document_name: str
    doc_type: str
    content: str
    score: float
    page_number: int | None = None
    section_title: str | None = None


def retrieve(query: str, db: Session, top_k: int = TOP_K) -> list[RetrievedChunk]:
    """Recupera os chunks mais relevantes dentre documentos ACTIVE.

    Documentos ARCHIVED são ignorados por padrão (spec: não usar como fonte principal).
    """
    provider = get_provider()
    try:
        q_embedding = provider.embed(query)
    except Exception:
        q_embedding = None

    active_docs = (
        db.query(PolicyDocument)
        .filter(PolicyDocument.status == "ACTIVE")
        .all()
    )
    if not active_docs:
        return []

    doc_map = {d.id: d for d in active_docs}
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id.in_([d.id for d in active_docs]))
        .all()
    )
    if not chunks:
        return []

    scored: list[tuple[DocumentChunk, float]] = []
    for chunk in chunks:
        embed_score = 0.0
        if q_embedding and chunk.embedding:
            try:
                embed_score = _cosine(q_embedding, chunk.embedding)
            except Exception:
                pass
        lex_score = _lexical(query, chunk.content)
        score = EMBED_WEIGHT * embed_score + LEXICAL_WEIGHT * lex_score
        scored.append((chunk, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    results = []
    for chunk, score in scored[:top_k]:
        doc = doc_map.get(chunk.document_id)
        results.append(RetrievedChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_name=doc.name if doc else "Desconhecido",
            doc_type=doc.doc_type if doc else "",
            content=chunk.content,
            score=round(score, 4),
            page_number=chunk.page_number,
            section_title=chunk.section_title,
        ))
    return results


# ─── busca textual fallback (sem embeddings) ──────────────────────────────────

def text_search(query: str, db: Session, top_k: int = TOP_K) -> list[RetrievedChunk]:
    """Busca por palavras-chave — fallback quando embeddings não estão disponíveis."""
    tokens = set(re.findall(r"\w{3,}", query.lower()))
    if not tokens:
        return []

    active_doc_ids = [
        d.id for d in db.query(PolicyDocument).filter(PolicyDocument.status == "ACTIVE").all()
    ]
    if not active_doc_ids:
        return []

    doc_map = {
        d.id: d
        for d in db.query(PolicyDocument)
        .filter(PolicyDocument.id.in_(active_doc_ids))
        .all()
    }
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id.in_(active_doc_ids))
        .all()
    )
    scored = [(c, _lexical(query, c.content)) for c in chunks if _lexical(query, c.content) > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    results = []
    for chunk, score in scored[:top_k]:
        doc = doc_map.get(chunk.document_id)
        results.append(RetrievedChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_name=doc.name if doc else "Desconhecido",
            doc_type=doc.doc_type if doc else "",
            content=chunk.content,
            score=round(score, 4),
            page_number=chunk.page_number,
            section_title=chunk.section_title,
        ))
    return results
