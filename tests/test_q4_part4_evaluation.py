import pytest
from evaluation.test_cases.dataset import EVALUATION_DATASET
from evaluation.false_positives.benchmark import run_false_positive_benchmark
from evaluation.latency.benchmark import run_latency_benchmark


def test_dataset_completeness_and_balance():
    """Verifies that evaluation test set covers all required signal categories."""
    categories = {item["category"] for item in EVALUATION_DATASET}
    assert "cross_sell" in categories
    assert "compliance" in categories
    assert "frustration" in categories
    assert "payment_difficulty" in categories
    assert "noisy_speech" in categories

    true_cases = [item for item in EVALUATION_DATASET if item["expected_nudge"]]
    false_cases = [item for item in EVALUATION_DATASET if not item["expected_nudge"]]
    assert len(true_cases) >= 6
    assert len(false_cases) >= 6


@pytest.mark.asyncio
async def test_false_positive_benchmark_metrics():
    """Executes false-positive analysis and asserts precision and recall meet SLAs."""
    summary = await run_false_positive_benchmark()
    m = summary["metrics"]

    assert m["precision"] >= 0.90, f"Precision {m['precision']} is below 90%"
    assert m["recall"] >= 0.90, f"Recall {m['recall']} is below 90%"
    assert m["f1_score"] >= 0.90, f"F1 {m['f1_score']} is below 0.90"
    assert m["accuracy"] >= 0.90, f"Accuracy {m['accuracy']} is below 90%"
    assert m["false_positives"] == 0, f"Expected 0 false positives, got {m['false_positives']}"


@pytest.mark.asyncio
async def test_latency_benchmark_percentiles():
    """Runs latency pipeline benchmark and asserts P50 and P95 comply with sub-second SLAs."""
    report = await run_latency_benchmark(num_iterations=1)
    c = report["components"]

    assert c["ASR"]["p50"] > 0
    assert c["ASR"]["p95"] > 0
    assert c["Signal_extraction"]["p50"] >= 0
    assert c["LLM_Jev_Nudge"]["p50"] >= 0
    assert c["Delivery_WebSocket"]["p50"] >= 0
    assert c["End_to_End_Total"]["p50"] > 0

    # Strict SLA check: End-to-End P95 must be under 250ms
    assert c["End_to_End_Total"]["p95"] < 250.0, f"End-to-end P95 {c['End_to_End_Total']['p95']}ms exceeded 250ms SLA"
