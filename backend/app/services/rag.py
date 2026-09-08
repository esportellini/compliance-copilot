"""Deterministic document indexing and evidence retrieval.

Offline retrieval is lexical BM25. A real provider embedding can refine the
order of lexically relevant candidates, but embeddings never create candidates
and RAG never participates in the compliance decision.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.document import DocumentChunk, PolicyDocument
from app.services.ai_provider import get_provider
from app.services.extractor import ExtractedPage, _extract_txt

MAX_CHUNK_CHARS = 700
TOP_K = 4
LEXICAL_WEIGHT = 0.8
EMBED_WEIGHT = 0.2

_PORTUGUESE_STOPWORDS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do",
    "dos", "e", "em", "esta", "este", "eu", "me", "na", "nas", "no",
    "nos", "o", "os", "ou", "para", "pela", "pelo", "por", "posso",
    "que", "r", "se", "ser", "um", "uma",
}

_PRODUCT_RETRIEVAL_TERMS = {
    "STOCK": "ação ações",
    "OPEN_FUND": "fundo fundos aberto abertos",
    "CLOSED_FUND": "fundo fundos fechado fechados",
    "CRYPTO": "cripto criptoativo criptoativos criptomoeda criptomoedas ativos digitais",
    "DERIVATIVE": "derivativo derivativos",
    "FIXED_INCOME": "renda fixa título títulos",
    "IPO": "ipo oferta ofertas públicas",
}


@dataclass
class Chunk:
    content: str
    page_number: int | None = None
    section_title: str | None = None


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


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def tokenize(text: str) -> list[str]:
    """Normalize policy text without discarding tickers or relevant numbers."""
    normalized = _fold(text)
    normalized = re.sub(r"(?<=\d)[.,](?=\d)", "", normalized)
    return [
        token
        for token in re.findall(r"[a-z0-9]+", normalized)
        if token not in _PORTUGUESE_STOPWORDS and (len(token) > 1 or token.isdigit())
    ]


def build_retrieval_query(
    question: str,
    *,
    product_name: str | None = None,
    identifier: str | None = None,
    product_type: str | None = None,
) -> str:
    """Add neutral product context without leaking the engine decision."""
    parts = [question, product_name or "", identifier or ""]
    parts.append(_PRODUCT_RETRIEVAL_TERMS.get((product_type or "").upper(), ""))
    return " ".join(part.strip() for part in parts if part and part.strip())


def _word_chunks(text: str, max_chars: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    pieces: list[str] = []
    current = ""
    for word in words:
        # A token longer than the limit stays intact; splitting it would violate
        # the no-cut-word guarantee.
        if not current:
            current = word
        elif len(current) + len(word) + 1 <= max_chars:
            current += f" {word}"
        else:
            pieces.append(current)
            current = word
    if current:
        pieces.append(current)
    return pieces


def _split_page(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split at paragraphs and sentences, falling back to whole words."""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    units: list[str] = []
    for paragraph in paragraphs:
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", paragraph)
            if sentence.strip()
        ]
        for sentence in sentences:
            if len(sentence) <= max_chars:
                units.append(sentence)
            else:
                units.extend(_word_chunks(sentence, max_chars))

    chunks: list[str] = []
    current = ""
    for unit in units:
        if not current:
            current = unit
        elif len(current) + len(unit) + 1 <= max_chars:
            current += f" {unit}"
        else:
            chunks.append(current)
            current = unit
    if current:
        chunks.append(current)
    return chunks


def chunk_pages(
    pages: list[ExtractedPage], max_chars: int = MAX_CHUNK_CHARS
) -> list[Chunk]:
    result: list[Chunk] = []
    for page in pages:
        for text in _split_page(page.text, max_chars=max_chars):
            result.append(
                Chunk(
                    content=text,
                    page_number=page.page_number,
                    section_title=page.section_title,
                )
            )
    return result


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def _embed(provider, text: str) -> list[float] | None:
    if not getattr(provider, "supports_semantic_embeddings", False):
        return None
    try:
        embedding = provider.embed(text)
    except (ConnectionError, TimeoutError):
        return None
    return embedding or None


def _replace_chunks(
    doc: PolicyDocument, pages: list[ExtractedPage], db: Session
) -> int:
    provider = get_provider()
    chunks = chunk_pages(pages)
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete(
        synchronize_session="fetch"
    )
    db.flush()

    for index, chunk in enumerate(chunks):
        db.add(
            DocumentChunk(
                document_id=doc.id,
                chunk_index=index,
                content=chunk.content,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                embedding=_embed(provider, chunk.content),
                char_count=len(chunk.content),
            )
        )
    doc.chunk_count = len(chunks)
    return len(chunks)


def index_document(doc: PolicyDocument, db: Session) -> int:
    """Index current extracted text through the shared TXT structure parser."""
    if not doc.extracted_text:
        return 0
    _, pages = _extract_txt(doc.extracted_text.encode("utf-8"))
    return _replace_chunks(doc, pages, db)


def index_document_from_pages(
    doc: PolicyDocument, pages: list[ExtractedPage], db: Session
) -> int:
    """Index extractor output while preserving page and section metadata."""
    return _replace_chunks(doc, pages, db)


def _bm25_scores(query_tokens: list[str], corpus: list[list[str]]) -> list[float]:
    if not query_tokens or not corpus:
        return [0.0] * len(corpus)
    document_count = len(corpus)
    average_length = sum(len(tokens) for tokens in corpus) / document_count or 1.0
    document_frequency = Counter(token for tokens in corpus for token in set(tokens))
    query_frequency = Counter(query_tokens)
    k1 = 1.5
    b = 0.75
    scores: list[float] = []
    for tokens in corpus:
        frequencies = Counter(tokens)
        length_factor = 1 - b + b * len(tokens) / average_length
        score = 0.0
        for token, query_count in query_frequency.items():
            frequency = frequencies[token]
            if not frequency:
                continue
            frequency_weight = frequency * (k1 + 1) / (frequency + k1 * length_factor)
            inverse_frequency = math.log(
                1
                + (document_count - document_frequency[token] + 0.5)
                / (document_frequency[token] + 0.5)
            )
            score += inverse_frequency * frequency_weight * query_count
        scores.append(score)
    return scores


def _content_key(content: str) -> str:
    return " ".join(tokenize(content))


def retrieve(query: str, db: Session, top_k: int = TOP_K) -> list[RetrievedChunk]:
    """Return only lexically relevant chunks from ACTIVE documents.

    The relevance gate requires a positive BM25 score, which is possible only
    when a chunk shares an informative normalized token with the query.
    Embeddings can reorder this candidate set but cannot admit unrelated text.
    """
    active_docs = (
        db.query(PolicyDocument)
        .filter(PolicyDocument.status == "ACTIVE")
        .order_by(PolicyDocument.id)
        .all()
    )
    if not active_docs:
        return []
    doc_map = {doc.id: doc for doc in active_docs}
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id.in_(doc_map))
        .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index, DocumentChunk.id)
        .all()
    )
    if not chunks:
        return []

    query_tokens = tokenize(query)
    corpus = [
        tokenize(f"{chunk.section_title or ''} {chunk.content}") for chunk in chunks
    ]
    lexical_scores = _bm25_scores(query_tokens, corpus)
    candidates = [
        (chunk, lexical_score)
        for chunk, lexical_score in zip(chunks, lexical_scores)
        if lexical_score > 0
    ]
    if not candidates:
        return []

    provider = get_provider()
    query_embedding = _embed(provider, query)
    ranked: list[tuple[DocumentChunk, float]] = []
    for chunk, lexical_raw in candidates:
        # x/(1+x) bounds exposed BM25 scores while preserving their order.
        lexical_score = lexical_raw / (1 + lexical_raw)
        if query_embedding and chunk.embedding:
            semantic_score = max(0.0, _cosine(query_embedding, chunk.embedding))
            score = LEXICAL_WEIGHT * lexical_score + EMBED_WEIGHT * semantic_score
        else:
            score = lexical_score
        ranked.append((chunk, score))

    ranked.sort(
        key=lambda item: (
            -item[1],
            item[0].document_id,
            item[0].chunk_index,
            item[0].id,
        )
    )

    results: list[RetrievedChunk] = []
    seen_content: set[str] = set()
    for chunk, score in ranked:
        content_key = _content_key(chunk.content)
        if content_key in seen_content:
            continue
        seen_content.add(content_key)
        doc = doc_map[chunk.document_id]
        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_name=doc.name,
                doc_type=doc.doc_type,
                content=chunk.content,
                score=round(score, 4),
                page_number=chunk.page_number,
                section_title=chunk.section_title,
            )
        )
        if len(results) == top_k:
            break
    return results


def text_search(query: str, db: Session, top_k: int = TOP_K) -> list[RetrievedChunk]:
    """Compatibility alias; primary retrieval already has lexical fallback."""
    return retrieve(query, db, top_k=top_k)
