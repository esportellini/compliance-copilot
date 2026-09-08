"""Behavioral coverage for deterministic policy-document retrieval."""
from __future__ import annotations

from app.models.copilot import CopilotAnswer, SourceReference
from app.models.document import DocumentChunk, PolicyDocument
from app.models.product import FinancialProduct
from app.models.user import User
from app.seed import seed
from app.services import ai_provider, rag
from app.services.copilot import CopilotInput, run_query
from app.services.extractor import ExtractedPage, extract_text
from app.tests.conftest import auth_header


def _document(db, *, name: str, status: str = "ACTIVE") -> PolicyDocument:
    doc = PolicyDocument(
        name=name,
        doc_type="INVESTMENT_POLICY",
        version="1",
        owner="compliance@test.local",
        status=status,
        extracted_text="conteúdo de teste",
    )
    db.add(doc)
    db.flush()
    return doc


def _chunk(
    db,
    doc: PolicyDocument,
    content: str,
    *,
    index: int = 0,
    page_number: int | None = None,
    section_title: str | None = None,
    embedding: list[float] | None = None,
) -> DocumentChunk:
    chunk = DocumentChunk(
        document_id=doc.id,
        chunk_index=index,
        content=content,
        page_number=page_number,
        section_title=section_title,
        embedding=embedding,
        char_count=len(content),
    )
    db.add(chunk)
    db.flush()
    return chunk


def test_tokenization_normalizes_accents_stopwords_punctuation_and_keeps_numbers():
    assert rag.tokenize("Posso AÇÕES, de R$ 100.000 no FUNDO?") == [
        "acoes",
        "100000",
        "fundo",
    ]


def test_txt_extraction_preserves_detectable_numbered_sections():
    text = """1. OBJETIVO
Texto introdutório.

2. FUNDOS ABERTOS
Aplicações em fundos abertos são disciplinadas por esta seção.
"""

    full_text, pages = extract_text(text.encode(), "politica.txt")

    assert full_text == text.strip()
    assert [(page.section_title, page.text) for page in pages] == [
        ("1. OBJETIVO", "Texto introdutório."),
        (
            "2. FUNDOS ABERTOS",
            "Aplicações em fundos abertos são disciplinadas por esta seção.",
        ),
    ]


def test_chunking_never_truncates_long_sentences_or_cuts_words():
    original = " ".join(f"palavra{i}" for i in range(80))

    chunks = rag.chunk_pages([ExtractedPage(text=original)], max_chars=80)

    assert " ".join(chunk.content for chunk in chunks) == original
    assert all(len(chunk.content) <= 80 for chunk in chunks)
    assert all(not chunk.content.endswith(" ") for chunk in chunks)


def test_indexing_preserves_page_and_section_and_is_idempotent(db):
    doc = _document(db, name="Política estruturada")
    pages = [
        ExtractedPage(
            text="Operações com ações exigem aprovação prévia.",
            page_number=3,
            section_title="3. AÇÕES",
        )
    ]

    first_count = rag.index_document_from_pages(doc, pages, db)
    db.flush()
    second_count = rag.index_document_from_pages(doc, pages, db)
    db.flush()

    stored = db.query(DocumentChunk).filter_by(document_id=doc.id).all()
    assert first_count == second_count == 1
    assert len(stored) == 1
    assert stored[0].page_number == 3
    assert stored[0].section_title == "3. AÇÕES"


def test_retrieval_uses_only_active_documents_and_deleted_chunks_disappear(db):
    active = _document(db, name="Ativa")
    archived = _document(db, name="Arquivada", status="ARCHIVED")
    draft = _document(db, name="Rascunho", status="DRAFT")
    _chunk(db, active, "ações exigem aprovação prévia")
    _chunk(db, archived, "ações exigem aprovação prévia")
    _chunk(db, draft, "ações exigem aprovação prévia")
    db.commit()

    assert [item.document_name for item in rag.retrieve("ações aprovação", db)] == [
        "Ativa"
    ]

    db.delete(active)
    db.commit()
    assert rag.retrieve("ações aprovação", db) == []


def test_relevance_gate_returns_no_sources_for_unrelated_query(db):
    doc = _document(db, name="Política")
    _chunk(db, doc, "operações com fundos abertos e ações de companhias listadas")
    db.commit()

    assert rag.retrieve("receita culinária para assar pão de queijo", db) == []


def test_retrieval_deduplicates_equal_evidence_and_has_stable_ties(db):
    first = _document(db, name="Documento A")
    second = _document(db, name="Documento B")
    first_chunk = _chunk(db, first, "ações exigem aprovação prévia")
    _chunk(db, second, "  AÇÕES exigem aprovação prévia.  ")
    _chunk(db, second, "fundos abertos possuem limite de investimento", index=1)
    db.commit()

    first_run = rag.retrieve("ações aprovação", db)
    second_run = rag.retrieve("ações aprovação", db)

    assert [item.chunk_id for item in first_run] == [first_chunk.id]
    assert [item.chunk_id for item in second_run] == [first_chunk.id]


def test_lexical_fallback_survives_expected_embedding_failure(db, monkeypatch):
    class UnavailableEmbeddingProvider:
        supports_semantic_embeddings = True

        def embed(self, text):
            raise ConnectionError("embedding service unavailable")

    doc = _document(db, name="Política")
    _chunk(db, doc, "fundos abertos disponíveis na plataforma")
    db.commit()
    monkeypatch.setattr(rag, "get_provider", lambda: UnavailableEmbeddingProvider())

    results = rag.retrieve("investir em fundos abertos", db)

    assert [item.document_name for item in results] == ["Política"]


def test_unexpected_embedding_programming_error_is_not_hidden(db, monkeypatch):
    class BrokenProvider:
        supports_semantic_embeddings = True

        def embed(self, text):
            raise ValueError("invalid embedding implementation")

    doc = _document(db, name="Política")
    _chunk(db, doc, "fundos abertos disponíveis na plataforma")
    db.commit()
    monkeypatch.setattr(rag, "get_provider", lambda: BrokenProvider())

    try:
        rag.retrieve("fundos abertos", db)
    except ValueError as exc:
        assert str(exc) == "invalid embedding implementation"
    else:
        raise AssertionError("unexpected provider bugs must remain visible")


def test_mock_provider_does_not_claim_to_generate_semantic_embeddings():
    provider = ai_provider.MockAIProvider()

    assert provider.supports_semantic_embeddings is False
    assert provider.embed("fundos abertos") == []


def test_real_embedding_is_only_an_additional_signal_after_lexical_gate(
    db, monkeypatch
):
    class SemanticProvider:
        supports_semantic_embeddings = True

        def embed(self, text):
            return [1.0, 0.0]

    first = _document(db, name="Sem alinhamento semântico")
    second = _document(db, name="Com alinhamento semântico")
    _chunk(db, first, "ações listadas exigem controle", embedding=[0.0, 1.0])
    aligned = _chunk(
        db,
        second,
        "ações listadas exigem controle",
        embedding=[1.0, 0.0],
    )
    unrelated = _chunk(
        db,
        second,
        "receitas culinárias e jardinagem",
        index=1,
        embedding=[1.0, 0.0],
    )
    db.commit()
    monkeypatch.setattr(rag, "get_provider", lambda: SemanticProvider())

    results = rag.retrieve("controle de ações", db)

    assert results[0].chunk_id == aligned.id
    assert unrelated.id not in [item.chunk_id for item in results]


def test_upload_and_process_preserve_txt_section_metadata(
    client, db, compliance_user
):
    headers = auth_header(client, "compliance@test.local")
    raw = b"""1. OBJETIVO
Texto introdutorio.

2. FUNDOS ABERTOS
Fundos abertos possuem regras de investimento.
"""

    uploaded = client.post(
        "/api/documents/upload",
        headers=headers,
        data={
            "name": "Política TXT",
            "doc_type": "INVESTMENT_POLICY",
            "version": "1",
            "owner": "compliance@test.local",
        },
        files={"file": ("politica.txt", raw, "text/plain")},
    )

    assert uploaded.status_code == 201
    doc_id = uploaded.json()["id"]
    assert uploaded.json()["chunk_count"] == 2

    processed = client.post(f"/api/documents/{doc_id}/process", headers=headers)
    assert processed.status_code == 200

    chunks = client.get(f"/api/documents/{doc_id}/chunks", headers=headers).json()
    assert [chunk["section_title"] for chunk in chunks] == [
        "1. OBJETIVO",
        "2. FUNDOS ABERTOS",
    ]


def test_copilot_api_and_source_reference_preserve_location_metadata(
    client, db, employee_user
):
    seed(db)
    headers = auth_header(client, "employee@test.local")

    response = client.post(
        "/api/copilot/query",
        headers=headers,
        json={
            "question": "Posso investir R$ 50.000 no Fundo Multimercado Alpha?",
            "product_name_hint": "FMALT",
            "amount": 50_000,
        },
    )

    assert response.status_code == 200
    source = response.json()["sources"][0]
    answer = db.query(CopilotAnswer).filter_by(query_id=response.json()["query_id"]).one()
    stored = db.query(SourceReference).filter_by(answer_id=answer.id).first()
    assert source["section_title"] == "2. FUNDOS ABERTOS"
    assert "page_number" in source
    assert stored.section_title == "2. FUNDOS ABERTOS"
    assert stored.page_number is None


def test_rag_presence_never_changes_structured_copilot_result(db):
    seed(db)
    user = db.query(User).filter_by(email="colaborador@demo.local").one()
    product = db.query(FinancialProduct).filter_by(identifier="FMALT").one()
    request = CopilotInput(
        user_id=user.id,
        question="Posso investir R$ 50.000 no Fundo Multimercado Alpha?",
        product_id=product.id,
        amount=50_000,
    )

    with_sources = run_query(request, db)
    policy = db.query(PolicyDocument).filter_by(
        name="Política de Investimentos v2.1"
    ).one()
    policy.status = "ARCHIVED"
    db.commit()
    without_sources = run_query(request, db)

    assert with_sources.sources
    assert without_sources.sources == []
    assert (
        with_sources.decision,
        with_sources.matched_rules,
        with_sources.next_action,
        with_sources.requires_human_review,
    ) == (
        without_sources.decision,
        without_sources.matched_rules,
        without_sources.next_action,
        without_sources.requires_human_review,
    )


def test_demo_policy_retrieval_returns_the_relevant_sections(db):
    seed(db)
    cases = [
        (
            "Posso investir R$ 50.000 no Fundo Multimercado Alpha?",
            "OPEN_FUND",
            "2. FUNDOS ABERTOS",
        ),
        (
            "Posso investir R$ 150.000 no Fundo Multimercado Alpha?",
            "OPEN_FUND",
            "2. FUNDOS ABERTOS",
        ),
        ("Posso comprar ações XPTO3?", "STOCK", "3. AÇÕES"),
        (
            "Posso comprar criptoativo CNOVA?",
            "CRYPTO",
            "4. ATIVOS DIGITAIS (CRIPTOMOEDAS)",
        ),
        ("ACME3 consta na lista restrita?", "STOCK", "5. LISTA RESTRITA"),
    ]

    for question, product_type, expected_section in cases:
        query = rag.build_retrieval_query(question, product_type=product_type)
        results = rag.retrieve(query, db)
        assert results, query
        assert results[0].section_title == expected_section, (
            query,
            [(item.section_title, item.score) for item in results],
        )

    assert rag.retrieve("como preparar uma receita de bolo de cenoura", db) == []
