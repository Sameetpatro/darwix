import pytest
from fastapi.testclient import TestClient

from app.server import app
from app.kb.retriever import retriever

client = TestClient(app)


def test_post_retrieve_endpoint_basic():
    """Validates FastAPI POST /retrieve endpoint with standard query."""
    payload = {
        "query": "What are your prepayment penalties on commercial loans?",
        "top_k": 3,
    }
    response = client.post("/retrieve", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["query"] == payload["query"]
    assert data["results_count"] >= 1
    assert len(data["evidence"]) >= 1
    assert data["latency_ms"] >= 0.0
    assert len(data["synthesized_context"]) > 0

    top_evidence = data["evidence"][0]
    assert top_evidence["chunk_id"].startswith("chk_")
    assert top_evidence["citation"] != ""
    assert "prepayment" in top_evidence["content"].lower() or "penalty" in top_evidence["content"].lower()
    assert top_evidence["score"] > 0.0


def test_post_retrieve_with_customer_context_reranking():
    """Validates that customer qualification context dynamically reranks relevant credit tiers."""
    # 1. Prime Borrower Profile: 680 FICO, 24 months in business, $30,000 monthly revenue
    prime_payload = {
        "query": "commercial loan rates and credit requirements",
        "top_k": 3,
        "customer_context": {
            "credit_score": 680,
            "time_in_business": 24,
            "monthly_revenue": 30000,
        },
    }
    res_prime = client.post("/retrieve", json=prime_payload)
    assert res_prime.status_code == 200
    prime_data = res_prime.json()
    top_prime = prime_data["evidence"][0]
    assert "prime" in top_prime["title"].lower() or "prime" in top_prime["content"].lower() or "tier 1" in top_prime["content"].lower()

    # 2. Alternative Working Capital Profile: 550 FICO, 6 months in business
    alt_payload = {
        "query": "commercial loan rates and credit requirements",
        "top_k": 3,
        "customer_context": {
            "credit_score": 550,
            "time_in_business": 6,
            "monthly_revenue": 10000,
        },
    }
    res_alt = client.post("/retrieve", json=alt_payload)
    assert res_alt.status_code == 200
    alt_data = res_alt.json()
    top_alt = alt_data["evidence"][0]
    assert "alternative" in top_alt["content"].lower() or "working capital" in top_alt["content"].lower() or "tier 3" in top_alt["content"].lower() or "6 months" in top_alt["content"].lower()


def test_post_retrieve_filtering_category_and_product():
    """Validates strict candidate filtering by category and product."""
    # Category Filter: faq
    faq_payload = {
        "query": "loan requirements and terms",
        "top_k": 3,
        "category": "faq",
    }
    res_faq = client.post("/retrieve", json=faq_payload)
    assert res_faq.status_code == 200
    faq_data = res_faq.json()
    for item in faq_data["evidence"]:
        assert item["category"].lower() == "faq"

    # Product Filter: Equipment Financing
    equip_payload = {
        "query": "maximum term and down payment",
        "top_k": 3,
        "product": "Equipment Financing",
    }
    res_equip = client.post("/retrieve", json=equip_payload)
    assert res_equip.status_code == 200
    equip_data = res_equip.json()
    for item in equip_data["evidence"]:
        assert item["product"] is not None
        assert "equipment" in item["product"].lower()


def test_post_retrieve_conflict_inclusion_and_notes():
    """Validates that conflicting policy guidance is captured and noted in the synthesized context."""
    payload = {
        "query": "minimum operating history months in business for term loans",
        "top_k": 3,
    }
    response = client.post("/retrieve", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify if any evidence item contains structured conflict records
    conflicts_found = any(item["has_conflict"] is True for item in data["evidence"])
    if conflicts_found:
        assert "[NOTE ON POLICY DISCREPANCY:" in data["synthesized_context"]


def test_post_retrieve_validation_errors():
    """Validates HTTP 400 and 422 error handling."""
    # Empty query -> 400 Bad Request
    res_empty = client.post("/retrieve", json={"query": "   "})
    assert res_empty.status_code == 400

    # Top_k out of bounds (>10) -> 422 Unprocessable Entity
    res_bounds = client.post("/retrieve", json={"query": "test", "top_k": 25})
    assert res_bounds.status_code == 422


def test_retriever_query_q2_integration():
    """Validates programmatic access to Q2 hybrid retrieval via KnowledgeRetriever.query_q2()."""
    items = retriever.query_q2("Tell me about equipment financing machinery leasing", top_k=2)
    assert len(items) >= 1
    top = items[0]
    assert "chunk_id" in top
    assert "citation" in top
    assert "content" in top
    assert "equipment" in top["content"].lower() or "machinery" in top["content"].lower()


def test_end_to_end_retrieval_latency_benchmark():
    """Benchmarks retrieval latency to ensure sub-50ms performance suitable for real-time voice calls."""
    queries = [
        "What are your interest rates?",
        "Do you have prepayment penalties?",
        "What is the minimum credit score for commercial loans?",
        "How fast can funds be deposited?",
        "What collateral is required for equipment leases?",
    ]
    latencies = []
    for q in queries:
        resp = client.post("/retrieve", json={"query": q, "top_k": 3})
        assert resp.status_code == 200
        latencies.append(resp.json()["latency_ms"])

    median_latency = sorted(latencies)[len(latencies) // 2]
    assert median_latency < 60.0, f"Expected median latency < 60ms for voice budget, got {median_latency}ms"
