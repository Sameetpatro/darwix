import time
from typing import List, Dict, Any
import numpy as np

from q2.retrieval.hybrid_search import hybrid_search_engine
from q2.api.retrieval_router import format_citation
from app.logging_config import logger


# Benchmark dataset with ground-truth target expectations
BENCHMARK_QUERIES = [
    {
        "query": "What are the prepayment penalties on commercial term loans?",
        "expected_category": "faq",
        "expected_keywords": ["prepayment", "penalty", "zero"],
        "expected_product": None,
    },
    {
        "query": "How fast can I get funded after submitting bank statements?",
        "expected_category": "faq",
        "expected_keywords": ["24", "48", "hours", "funding"],
        "expected_product": None,
    },
    {
        "query": "Does applying hurt my personal credit score?",
        "expected_category": "faq",
        "expected_keywords": ["soft", "inquiry", "credit score"],
        "expected_product": None,
    },
    {
        "query": "What are the interest rates and requirements for Tier 1 Prime Commercial loans?",
        "expected_category": "product",
        "expected_keywords": ["5.99%", "680", "prime"],
        "expected_product": "Term Loan",
    },
    {
        "query": "What are the rates and terms for Standard Commercial credit Tier 2?",
        "expected_category": "product",
        "expected_keywords": ["11.00%", "620", "standard"],
        "expected_product": "Term Loan",
    },
    {
        "query": "What is the maximum financing amount for heavy construction machinery?",
        "expected_category": "product",
        "expected_keywords": ["2,000,000", "84 months", "construction"],
        "expected_product": "Equipment Financing",
    },
    {
        "query": "What collateral is required for commercial fleet vehicles?",
        "expected_category": "product",
        "expected_keywords": ["vehicle title lien", "fleet"],
        "expected_product": "Equipment Financing",
    },
    {
        "query": "What is the minimum operating history required for short-term working capital?",
        "expected_category": "qualification",
        "expected_keywords": ["6 months", "operating history"],
        "expected_product": "Term Loan",
    },
    {
        "query": "What industries are strictly restricted or prohibited from funding?",
        "expected_category": "policy",
        "expected_keywords": ["gambling", "cryptocurrency", "cannabis"],
        "expected_product": None,
    },
    {
        "query": "What is the maximum unsecured loan leverage ratio relative to monthly revenue?",
        "expected_category": "faq",
        "expected_keywords": ["leverage", "3.5x", "revenue"],
        "expected_product": None,
    },
    {
        "query": "Your interest rates are way too high compared to traditional bank loans.",
        "expected_category": "objection",
        "expected_keywords": ["5.99%", "merchant cash advance", "rates"],
        "expected_product": None,
    },
    {
        "query": "What are the SBA 7(a) prime guarantee interest rate spreads?",
        "expected_category": "product",
        "expected_keywords": ["prime +", "sba", "660"],
        "expected_product": "Term Loan",
    },
]


def evaluate_retrieval_benchmark() -> Dict[str, Any]:
    """
    Evaluates the hybrid search engine against ground-truth benchmark queries.
    Computes Precision@1, Recall@3, MRR (Mean Reciprocal Rank), and latency statistics.
    """
    precisions_at_1 = []
    recalls_at_3 = []
    reciprocal_ranks = []
    latencies_ms = []

    print("\n" + "=" * 80)
    print("           DARWIX Q2 HYBRID RAG RETRIEVAL EVALUATION BENCHMARK")
    print("=" * 80)

    for i, item in enumerate(BENCHMARK_QUERIES, 1):
        q = item["query"]
        expected_cat = item["expected_category"]
        expected_kw = item["expected_keywords"]

        t0 = time.time()
        results = hybrid_search_engine.search(query=q, top_k=3)
        latency = (time.time() - t0) * 1000
        latencies_ms.append(latency)

        hit_p1 = False
        hit_r3 = False
        first_match_rank = 0

        for rank, res in enumerate(results, 1):
            content_lower = (res.chunk.content + " " + res.chunk.title).lower()
            # Match condition: at least 1 expected keyword appears in content
            matches_kw = any(kw.lower() in content_lower for kw in expected_kw)
            matches_cat = (res.chunk.category.lower() == expected_cat.lower()) if expected_cat else True

            if matches_kw:
                if rank == 1:
                    hit_p1 = True
                hit_r3 = True
                if first_match_rank == 0:
                    first_match_rank = rank

        precisions_at_1.append(1.0 if hit_p1 else 0.0)
        recalls_at_3.append(1.0 if hit_r3 else 0.0)
        reciprocal_ranks.append(1.0 / first_match_rank if first_match_rank > 0 else 0.0)

        top_chunk = results[0].chunk if results else None
        print(f"[{i:02d}] Query: '{q[:48]}...'")
        print(f"     Rank 1: '{top_chunk.title if top_chunk else 'None'}' | Score: {results[0].fused_score:.6f} | Latency: {latency:.2f}ms")
        print(f"     P@1: {'PASS' if hit_p1 else 'FAIL'} | R@3: {'PASS' if hit_r3 else 'FAIL'} | Match Rank: {first_match_rank}")
        print("-" * 80)

    mean_p1 = float(np.mean(precisions_at_1))
    mean_r3 = float(np.mean(recalls_at_3))
    mrr = float(np.mean(reciprocal_ranks))
    median_lat = float(np.median(latencies_ms))
    p95_lat = float(np.percentile(latencies_ms, 95))

    summary = {
        "total_queries": len(BENCHMARK_QUERIES),
        "precision_at_1": round(mean_p1, 4),
        "recall_at_3": round(mean_r3, 4),
        "mean_reciprocal_rank": round(mrr, 4),
        "median_latency_ms": round(median_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
    }

    print("\n" + "=" * 80)
    print("                              EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Total Benchmark Queries : {summary['total_queries']}")
    print(f"Precision @ 1           : {summary['precision_at_1'] * 100:.1f}%")
    print(f"Recall @ 3              : {summary['recall_at_3'] * 100:.1f}%")
    print(f"Mean Reciprocal Rank    : {summary['mean_reciprocal_rank']:.4f}")
    print(f"Median Latency          : {summary['median_latency_ms']:.2f} ms")
    print(f"P95 Latency             : {summary['p95_latency_ms']:.2f} ms")
    print("=" * 80 + "\n")

    return summary


if __name__ == "__main__":
    evaluate_retrieval_benchmark()
