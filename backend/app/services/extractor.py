"""Extração de texto de PDF, DOCX e TXT.

Retorna uma lista de páginas/seções: cada item tem (text, page_or_section, title).
Isso alimenta o RAG com metadata de localização — o chunker usa essa informação
para preservar a página/seção de origem em cada chunk.

Não salva arquivos em disco além do necessário para processamento em memória.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass


@dataclass
class ExtractedPage:
    text: str
    page_number: int | None = None   # PDF: número da página (1-indexed)
    section_title: str | None = None  # DOCX: heading mais recente


def extract_text(raw: bytes, filename: str) -> tuple[str, list[ExtractedPage]]:
    """Retorna (full_text, pages_with_metadata).

    Para TXT: uma única "página" sem número.
    Para PDF: uma página por folha.
    Para DOCX: uma seção por heading de nível 1–2.
    """
    fname = filename.lower()
    if fname.endswith(".pdf"):
        return _extract_pdf(raw)
    if fname.endswith(".docx"):
        return _extract_docx(raw)
    # TXT / fallback
    return _extract_txt(raw)


def _extract_txt(raw: bytes) -> tuple[str, list[ExtractedPage]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")
    text = text.strip()
    return text, [ExtractedPage(text=text)]


def _extract_pdf(raw: bytes) -> tuple[str, list[ExtractedPage]]:
    try:
        from pypdf import PdfReader
    except ImportError:
        # pypdf não instalado — retorna texto vazio com aviso
        msg = "[Extração de PDF indisponível: instale pypdf]"
        return msg, [ExtractedPage(text=msg)]

    reader = PdfReader(io.BytesIO(raw))
    pages: list[ExtractedPage] = []
    full_parts: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(ExtractedPage(text=text, page_number=i))
            full_parts.append(text)
    full_text = "\n\n".join(full_parts)
    return full_text, pages


def _extract_docx(raw: bytes) -> tuple[str, list[ExtractedPage]]:
    try:
        import docx
    except ImportError:
        msg = "[Extração de DOCX indisponível: instale python-docx]"
        return msg, [ExtractedPage(text=msg)]

    doc = docx.Document(io.BytesIO(raw))
    sections: list[ExtractedPage] = []
    current_title: str | None = None
    current_parts: list[str] = []
    full_parts: list[str] = []

    heading_styles = {"heading 1", "heading 2", "título 1", "título 2"}

    def flush():
        if current_parts:
            t = "\n".join(current_parts).strip()
            if t:
                sections.append(ExtractedPage(text=t, section_title=current_title))

    for para in doc.paragraphs:
        style_name = para.style.name.lower() if para.style else ""
        text = para.text.strip()
        if not text:
            continue
        full_parts.append(text)
        if any(h in style_name for h in heading_styles):
            flush()
            current_title = text
            current_parts = []
        else:
            current_parts.append(text)

    flush()
    # se não havia headings, tudo em uma seção
    if not sections:
        full_text = "\n\n".join(full_parts)
        sections = [ExtractedPage(text=full_text)]

    return "\n\n".join(full_parts), sections
