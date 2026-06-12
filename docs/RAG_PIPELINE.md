# RAG Pipeline

## Overview

Retrieval-Augmented Generation connects policy documents to Copilot answers.
The engine's decision is always authoritative — RAG provides supporting evidence.

## Pipeline Steps

```
1. Document upload (PDF / DOCX / TXT)
   └── Text extraction (pypdf / python-docx / utf-8 fallback)

2. Chunking
   ├── Split by paragraphs (double newline)
   ├── Max chunk size: ~700 characters
   ├── Sentence-boundary aware splitting
   └── Metadata preserved: page_number (PDF), section_title (DOCX)

3. Embedding
   ├── MockAIProvider: SHA-256 hash → normalized 256-dim vector (offline)
   └── OpenAIProvider: text-embedding-3-small → 1536-dim vector

4. Storage
   └── JSONB column (swap-ready for pgvector.Vector(1536) in production)

5. Retrieval at query time
   ├── Embed the query
   ├── Filter: only ACTIVE documents (ARCHIVED are excluded)
   ├── Score each chunk:
   │   score = 0.7 × cosine_similarity + 0.3 × lexical_overlap
   └── Return top-K chunks (default: 4)

6. Source enforcement
   └── If no chunk AND no rule matched → decision forced to INCONCLUSIVE
```

## Upgrading to pgvector

```sql
-- 1. Enable extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Change column type (in migration)
ALTER TABLE document_chunks
  ALTER COLUMN embedding TYPE vector(1536)
  USING embedding::vector;

-- 3. Add index
CREATE INDEX ON document_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

Then update the retrieval query in `rag.py` to use `<=>` operator.

## Document Lifecycle

```
Upload → DRAFT → (set version + owner) → Process → ACTIVE → Archive → ARCHIVED
```

Only ACTIVE documents feed the RAG. Archiving immediately removes the document
from future queries without deleting its chunks (which remain for audit trail).
