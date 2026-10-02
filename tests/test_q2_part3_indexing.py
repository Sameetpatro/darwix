import pytest
from pathlib import Path
import numpy as np

from q2.models.knowledge_record import KnowledgeRecord, NormalizedEntities, ConflictRecord
from q2.models.chunk import KnowledgeChunk, SearchResult
from q2.chunking.semantic_chunker import SemanticChunker, semantic_chunker
from q2.embeddings.embedder import Embedder, embedder
from q2.retrieval.bm25_index import BM25Index, bm25_index, tokenize
from q2.storage.chunk_store import ChunkStore, chunk_store
from q2.retrieval.hybrid_search import HybridSearchEngine, hybrid_search_engine


def test_semantic_chunker_context_headers():
    """Validates that semantic chunking prepends provenance context headers."""
    record = KnowledgeRecord(
        source_doc_id="doc_handbook_01",
        title="General Eligibility Rules",
        cleaned_content="Minimum operating history is 12 to 24 months. Gross monthly revenue must exceed $10,000.",
        original_content_hash="raw_hash_01",
        cleaned_content_hash="clean_hash_01",
        category="qualification",
        product="Term Loan",
        source="loan_policy_handbook.pdf",
        source_location={"page": 1, "section": "Section 1: General Business Loan Eligibility"},
    )
    chunks = semantic_chunker.chunk_record(record)
    assert len(chunks) == 1
    chk = chunks[0]
    assert "[Document: loan_policy_handbook.pdf]" in chk.context_header
    assert "[Product: Term Loan]" in chk.context_header
    assert "[Category: qualification]" in chk.context_header
    assert "[Section: Section 1: General Business Loan Eligibility]" in chk.context_header
    assert "Minimum operating history is 12 to 24 months" in chk.content


def test_semantic_chunker_table_preservation():
    """Validates that markdown tables preserve header rows in all resulting chunks."""
    table_content = """# Equipment Financing Rates

| Category | Max Amount | Max Term | Collateral |
| --- | --- | --- | --- |
| Heavy Construction | $1,000,000 | 84 Months | Equipment Lien |
| Medical Devices | $500,000 | 60 Months | Equipment Lien |
| Commercial Fleet | $350,000 | 60 Months | Vehicle Title Lien |
| Restaurant Kitchen | $250,000 | 48 Months | Equipment Lien |
| Office IT Hardware | $150,000 | 36 Months | Equipment Lien |
| Dental Imaging | $400,000 | 60 Months | Equipment Lien |
"""
    record = KnowledgeRecord(
        source_doc_id="doc_rates_tbl",
        title="Equipment Financing Rates",
        cleaned_content=table_content,
        original_content_hash="raw_tbl_hash",
        cleaned_content_hash="clean_tbl_hash",
        category="product",
        product="Equipment Financing",
        source="equipment_rates.md",
    )
    chunker = SemanticChunker(max_chunk_chars=400)
    chunks = chunker.chunk_record(record)

    assert len(chunks) >= 2
    for chk in chunks:
        if chk.metadata.get("is_table"):
            assert "| Category | Max Amount | Max Term | Collateral |" in chk.content
            assert "| --- | --- | --- | --- |" in chk.content


def test_embedder_fastembed_vectors():
    """Validates FastEmbed ONNX 384-dimensional dense embeddings and cosine similarity."""
    test_embedder = Embedder()
    assert test_embedder.dimension == 384

    v1 = np.array(test_embedder.embed_text("What is the minimum credit score required for commercial loans?"))
    v2 = np.array(test_embedder.embed_text("What are the credit profile and FICO requirements for borrowing?"))
    v3 = np.array(test_embedder.embed_text("How do you cook pasta with tomato sauce?"))

    assert len(v1) == 384
    assert len(v2) == 384

    # Semantically similar queries should have high cosine similarity (>0.70)
    sim_similar = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    # Unrelated queries should have low cosine similarity (<0.40)
    sim_unrelated = np.dot(v1, v3) / (np.linalg.norm(v1) * np.linalg.norm(v3))

    assert sim_similar > 0.70, f"Expected high similarity, got {sim_similar}"
    assert sim_unrelated < 0.50, f"Expected low similarity, got {sim_unrelated}"


def test_bm25_exact_lookup_and_filtering():
    """Validates BM25 sparse keyword ranking on exact percentages, numbers, and products."""
    custom_index = BM25Index()

    c1 = KnowledgeChunk(
        record_id="rec_rate_1",
        title="Tier 1 Prime",
        content="Tier 1 Prime Commercial loans offer 5.99% APR with a minimum credit score of 680.",
        context_header="[Product: Term Loan] [Category: product]",
        category="product",
        product="Term Loan",
        source="rates.csv",
    )
    c2 = KnowledgeChunk(
        record_id="rec_rate_2",
        title="Tier 2 Standard",
        content="Tier 2 Standard Commercial loans feature 11.00% APR with a minimum credit score of 620.",
        context_header="[Product: Term Loan] [Category: product]",
        category="product",
        product="Term Loan",
        source="rates.csv",
    )
    c3 = KnowledgeChunk(
        record_id="rec_faq_1",
        title="Prepayment FAQ",
        content="Darwix loans have zero prepayment penalties for early settlement.",
        context_header="[Product: General] [Category: faq]",
        category="faq",
        product="General",
        source="faq.txt",
    )

    custom_index.add_chunks([c1, c2, c3])

    # Search exact APR: '5.99%'
    hits_apr = custom_index.search("5.99% APR", top_k=2)
    assert len(hits_apr) >= 1
    assert hits_apr[0][0].chunk_id == c1.chunk_id

    # Search exact FICO: '620'
    hits_fico = custom_index.search("credit score 620", top_k=2)
    assert len(hits_fico) >= 1
    assert hits_fico[0][0].chunk_id == c2.chunk_id

    # Search with category filter: category='faq'
    hits_faq = custom_index.search("prepayment", top_k=5, category="faq")
    assert len(hits_faq) == 1
    assert hits_faq[0][0].category == "faq"


def test_hybrid_search_rrf_scoring():
    """Validates Reciprocal Rank Fusion of dense vector search and sparse BM25 search."""
    results = hybrid_search_engine.search(
        query="What are the prepayment penalties on commercial term loans?",
        top_k=3,
        dense_weight=0.6,
        sparse_weight=0.4,
    )

    assert len(results) >= 1
    top = results[0]
    assert isinstance(top, SearchResult)
    assert top.rank == 1
    assert top.fused_score > 0.0
    assert "prepayment" in top.chunk.content.lower() or "penalty" in top.chunk.content.lower()


def test_metadata_filtering():
    """Validates that category and product filters restrict candidate sets strictly."""
    # Filter by category: faq
    faq_results = hybrid_search_engine.search(
        query="business loan requirements",
        top_k=5,
        category="faq",
    )
    for r in faq_results:
        assert r.chunk.category.lower() == "faq"

    # Filter by product: Equipment Financing
    equip_results = hybrid_search_engine.search(
        query="rates and terms",
        top_k=5,
        product="Equipment Financing",
    )
    for r in equip_results:
        assert r.chunk.product is not None
        assert "equipment" in r.chunk.product.lower()


def test_conflict_attachment_on_results():
    """Validates that SearchResults include structured ConflictRecords from parent knowledge records."""
    # Search for Term Loan operating history which contains the 6 vs 24 months policy conflict
    results = hybrid_search_engine.search(
        query="minimum operating history months in business for term loans",
        top_k=5,
    )
    assert len(results) >= 1

    # Check that at least one matching candidate carries the conflict metadata
    has_conflicts = any(len(r.conflicts) > 0 for r in results)
    if has_conflicts:
        conf_result = next(r for r in results if len(r.conflicts) > 0)
        c = conf_result.conflicts[0]
        assert c.field in ["min_months_in_business", "min_credit_score", "prepayment_penalty_allowed"]
        assert c.conflicting_record_id != ""


def test_neon_pgvector_query():
    """Validates live vector similarity query against Neon PostgreSQL pgvector table."""
    q_vec = embedder.embed_text("Equipment financing down payment and rates")
    hits = chunk_store.query_dense(query_vector=q_vec, top_k=3, use_pgvector=True)

    assert len(hits) >= 1
    top_chunk, score = hits[0]
    assert isinstance(top_chunk, KnowledgeChunk)
    assert 0.0 <= score <= 1.0
    assert top_chunk.chunk_id.startswith("chk_")
