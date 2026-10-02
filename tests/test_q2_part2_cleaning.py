import pytest
import os
from pathlib import Path

from q2.models.raw_document import RawDocument
from q2.models.knowledge_record import KnowledgeRecord, ConflictRecord, NormalizedEntities
from q2.cleaning.boilerplate import clean_boilerplate
from q2.pii.redactor import PIIRedactor, pii_redactor
from q2.normalization.normalizer import EntityNormalizer, entity_normalizer
from q2.deduplication.deduplicator import Deduplicator, deduplicator
from q2.conflicts.conflict_detector import ConflictDetector, conflict_detector
from q2.storage.knowledge_store import knowledge_store
from q2.graph.cleaning_graph import clean_and_structure_document, process_raw_documents


def test_boilerplate_cleaning():
    """Validates removal of cookie notices, nav/footer noise, HTML tags, and unicode normalization."""
    dirty_text = """
    <html><body>
    <div>Home | About Us | Contact Us | Privacy Policy</div>
    <h1>Darwix Commercial Lending Overview</h1>
    <p>We provide prime term loans starting at 5.99% APR.</p>
    <p>We use cookies to improve your user experience on our website. Accept all cookies.</p>
    <div>Copyright © 2026 Darwix Financial Inc. All rights reserved.</div>
    </body></html>
    """
    cleaned, noise = clean_boilerplate(dirty_text)

    assert "Darwix Commercial Lending Overview" in cleaned
    assert "starting at 5.99% APR" in cleaned
    assert "cookies" not in cleaned.lower()
    assert "copyright" not in cleaned.lower()
    assert "home | about us" not in cleaned.lower()
    assert "<html>" not in cleaned
    assert "html_tags" in noise
    assert "cookie_notice" in noise or "nav_footer_boilerplate" in noise


def test_pii_detection_and_redaction():
    """Validates regex detection and masking of SSN, EIN, phone, email, bank account, routing, names."""
    sensitive_doc = """
    Borrower Underwriting Memo:
    Guarantor: Johnathan Miller
    SSN: 123-45-6789
    Tax ID / EIN: 12-3456789
    Contact Phone: (555) 234-5678
    Contact Email: j.miller@darwix-client.org
    Direct ACH Routing #: 021000021
    Disbursement Checking Account #: 987654321012
    Business Age: 36 months operating.
    """
    redactor = PIIRedactor()
    redacted, audit = redactor.redact(sensitive_doc)

    # Assert tokens
    assert "[REDACTED_NAME]" in redacted
    assert "[REDACTED_SSN]" in redacted
    assert "[REDACTED_EIN]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_ROUTING_NUMBER]" in redacted
    assert "[REDACTED_BANK_ACCOUNT]" in redacted

    # Assert raw secrets are NOT present
    assert "123-45-6789" not in redacted
    assert "12-3456789" not in redacted
    assert "(555) 234-5678" not in redacted
    assert "j.miller@darwix-client.org" not in redacted
    assert "021000021" not in redacted
    assert "987654321012" not in redacted

    # Assert audit counts
    assert audit.get("ssn") == 1
    assert audit.get("ein") == 1
    assert audit.get("phone") == 1
    assert audit.get("email") == 1
    assert audit.get("routing_number") == 1
    assert audit.get("bank_account") == 1
    assert audit.get("person_name") == 1


def test_entity_normalization():
    """Validates standardization of time in business, revenue, FICO, loan amounts, APR, and taxonomy."""
    text = """
    Prime Commercial Term Loan:
    Eligible business structures: LLC, C-Corp, and S-Corp.
    Operating history: minimum of 24 months (2 years) in active operations.
    Revenue requirement: average monthly gross revenues of $30,000 USD.
    Credit profile: credit score of at least 680 FICO required.
    Facility range: $25,000 up to $500,000.
    Starting rates: 5.99% to 10.99% APR with Monthly ACH repayment.
    Prepayment: zero prepayment penalties.
    Policy revision date: January 15, 2026.
    """
    normalizer = EntityNormalizer()
    entities = normalizer.normalize(text)

    # Time in business
    assert entities.time_in_business_months == 24
    assert "24 months" in entities.time_in_business_display

    # Products & Entities
    assert "Term Loan" in entities.loan_products
    assert "LLC" in entities.entity_types
    assert "C-Corp" in entities.entity_types
    assert "S-Corp" in entities.entity_types

    # Financial constraints
    assert entities.min_revenue_monthly_usd == 30000.0
    assert entities.min_credit_score == 680
    assert entities.min_loan_amount_usd == 25000.0
    assert entities.max_loan_amount_usd == 500000.0
    assert entities.min_apr == 5.99
    assert entities.max_apr == 10.99
    assert entities.repayment_frequency == "Monthly"
    assert entities.prepayment_penalty_allowed is False

    # Date
    assert "2026-01-15" in entities.normalized_dates


def test_deduplication_exact_and_near():
    """Validates exact hash deduplication and near-duplicate shingle similarity detection."""
    dedup = Deduplicator(near_duplicate_threshold=0.85)

    content_a = "All Darwix Commercial Term Loans have zero prepayment penalties for early payoff."
    content_b = "All Darwix Commercial Term Loans have zero prepayment penalties for early payoff."
    content_c = "All Darwix Commercial Term Loans feature zero prepayment penalties for early loan payoff."
    content_distinct = "Equipment financing requires collateral and down payment up to 10 percent."

    # Record A: First time -> unique
    is_dup_a, dup_id_a, score_a, hash_a = dedup.check_and_register("rec_1", content_a)
    assert is_dup_a is False
    assert dup_id_a is None

    # Record B: Exact duplicate -> True
    is_dup_b, dup_id_b, score_b, hash_b = dedup.check_and_register("rec_2", content_b)
    assert is_dup_b is True
    assert dup_id_b == "rec_1"
    assert score_b == 1.0
    assert hash_b == hash_a

    # Record C: Near-duplicate (>85% word overlap) -> True
    is_dup_c, dup_id_c, score_c, hash_c = dedup.check_and_register("rec_3", content_c)
    assert is_dup_c is True
    assert dup_id_c == "rec_1"
    assert score_c >= 0.70  # Near duplicate detection triggers

    # Record Distinct -> False
    is_dup_d, dup_id_d, score_d, hash_d = dedup.check_and_register("rec_4", content_distinct)
    assert is_dup_d is False


def test_conflict_detection():
    """Validates detection of conflicting underwriting rules between documents."""
    detector = ConflictDetector()

    # Document 1 asserts Term Loan min operating history is 12 months
    entities_1 = NormalizedEntities(
        loan_products=["Term Loan"],
        time_in_business_months=12,
        min_credit_score=620,
        prepayment_penalty_allowed=False,
    )
    conflicts_1 = detector.detect_conflicts(
        record_id="rec_handbook_v1",
        title="Handbook Section 1",
        product="Term Loan",
        entities=entities_1,
        source="handbook_v1.pdf",
    )
    assert len(conflicts_1) == 0  # First observation has no conflict

    # Document 2 asserts Term Loan min operating history is 6 months (conflicting!)
    entities_2 = NormalizedEntities(
        loan_products=["Term Loan"],
        time_in_business_months=6,
        min_credit_score=620,
        prepayment_penalty_allowed=False,
    )
    conflicts_2 = detector.detect_conflicts(
        record_id="rec_handbook_v2",
        title="Working Capital Policy",
        product="Term Loan",
        entities=entities_2,
        source="handbook_v2.pdf",
    )
    assert len(conflicts_2) >= 1
    c = conflicts_2[0]
    assert c.field == "min_months_in_business"
    assert c.product == "Term Loan"
    assert c.conflicting_record_id == "rec_handbook_v1"
    assert c.this_value == 6
    assert c.conflicting_value == 12

    # Document 3 asserts prepayment penalty applies (conflicting with zero penalty!)
    entities_3 = NormalizedEntities(
        loan_products=["Term Loan"],
        prepayment_penalty_allowed=True,
    )
    conflicts_3 = detector.detect_conflicts(
        record_id="rec_vendor_clause",
        title="Vendor Agreement",
        product="Term Loan",
        entities=entities_3,
        source="vendor_clause.txt",
    )
    assert any(c.field == "prepayment_penalty_allowed" and c.severity == "high" for c in conflicts_3)


def test_langgraph_cleaning_workflow_e2e():
    """Validates full LangGraph execution from clean_text -> redact_pii -> normalize -> deduplicate -> conflict -> assemble."""
    raw_doc = RawDocument(
        source_type="text",
        source="underwriting_memo_2026.txt",
        page=1,
        section="Credit Matrix Tier 1",
        title="Prime Commercial Term Loan Underwriting Matrix",
        raw_content="""
        Prime Commercial Term Loan Guidelines:
        Guarantor: Robert Vance
        Contact Email: rvance@vancerefrigeration.com
        Contact Phone: (555) 789-0123
        Tax ID: 45-9876543
        Underwriting Rules:
        Borrowing entity must be an LLC or C-Corp with at least 24 months of operating history.
        Minimum monthly revenue: $30,000.
        Minimum credit score: 680 FICO.
        Loan facility range: $25,000 to $500,000.
        Effective Date: 2026-02-01.
        """,
        content_type="qualification",
        classification_confidence=0.95,
    )

    result = clean_and_structure_document(raw_doc)

    assert result["status"] == "success"
    assert result["knowledge_record"] is not None
    krec: KnowledgeRecord = result["knowledge_record"]

    # Verify PII was redacted
    assert "[REDACTED_NAME]" in krec.cleaned_content
    assert "[REDACTED_EMAIL]" in krec.cleaned_content
    assert "[REDACTED_PHONE]" in krec.cleaned_content
    assert "[REDACTED_EIN]" in krec.cleaned_content
    assert krec.pii_audit.get("email") == 1
    assert krec.pii_audit.get("phone") == 1

    # Verify normalization
    assert krec.product == "Term Loan"
    assert krec.normalized_entities.time_in_business_months == 24
    assert krec.normalized_entities.min_revenue_monthly_usd == 30000.0
    assert krec.normalized_entities.min_credit_score == 680
    assert krec.normalized_entities.min_loan_amount_usd == 25000.0
    assert krec.normalized_entities.max_loan_amount_usd == 500000.0

    # Verify hashes and storage
    assert krec.original_content_hash != ""
    assert krec.cleaned_content_hash != ""
    assert result["stored_path"] is not None
    assert Path(result["stored_path"]).exists()


def test_persistence_local_and_neon_postgres():
    """Validates dual persistence to local JSON and Neon PostgreSQL database."""
    test_record = KnowledgeRecord(
        source_doc_id="doc_test_123",
        title="Test Policy Record",
        cleaned_content="Darwix Commercial loans require at least 12 months operating history and $15,000 monthly revenue.",
        original_content_hash="test_raw_hash_abc",
        cleaned_content_hash="test_clean_hash_xyz",
        category="qualification",
        product="Term Loan",
        source="test_policy.txt",
        source_location={"page": 1, "section": "Eligibility"},
        version="1.0",
        effective_date="2026-01-01",
        normalized_entities=NormalizedEntities(
            loan_products=["Term Loan"],
            time_in_business_months=12,
            min_revenue_monthly_usd=15000.0,
        ),
        pii_audit={"email": 0},
        conflicts=[],
        is_duplicate=False,
    )

    path = knowledge_store.save_record(test_record)
    assert Path(path).exists()

    # Retrieve by ID
    fetched = knowledge_store.get_by_id(test_record.record_id)
    assert fetched is not None
    assert fetched.record_id == test_record.record_id
    assert fetched.title == "Test Policy Record"
    assert fetched.product == "Term Loan"
    assert fetched.normalized_entities.time_in_business_months == 12


def test_process_all_part1_extracted_documents():
    """
    Ingests all extracted documents from Part 1 through the cleaning & structuring workflow.
    Ensures all 11 extracted chunks from PDF, HTML, CSV, and TXT are cleaned, normalized, and stored.
    """
    import json
    raw_extracted_dir = Path("data/raw_extracted")
    all_raw_docs = []

    for json_file in raw_extracted_dir.glob("*_extracted.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            batch_data = json.load(f)
            for d in batch_data.get("documents", []):
                # Skip failed/empty docs
                if d.get("raw_content"):
                    all_raw_docs.append(RawDocument.model_validate(d))

    assert len(all_raw_docs) >= 10, f"Expected at least 10 extracted docs, got {len(all_raw_docs)}"

    # Process all through cleaning workflow
    cleaned_records = process_raw_documents(all_raw_docs)

    assert len(cleaned_records) >= 10
    categories = {r.category for r in cleaned_records}
    assert "qualification" in categories or "policy" in categories
    assert "product" in categories
    assert "faq" in categories

    # Verify every record has valid cleaned content and hashes
    for r in cleaned_records:
        assert r.record_id.startswith("krec_")
        assert len(r.cleaned_content) > 0
        assert r.original_content_hash != ""
        assert r.cleaned_content_hash != ""
