import pytest
from pathlib import Path

from q2.models.raw_document import RawDocument, TableData
from q2.parsers.pdf_parser import PDFParser
from q2.parsers.html_parser import HTMLParser
from q2.parsers.table_parser import TableParser
from q2.parsers.text_parser import TextParser
from q2.classification.laya_client import laya_classifier
from q2.graph.ingestion_graph import ingest_file


RAW_DIR = Path("data/raw")


def test_pdf_parser_extraction():
    """Validates PDF parsing, page numbering, heading detection, and table detection."""
    pdf_path = RAW_DIR / "loan_policy_handbook.pdf"
    assert pdf_path.exists(), "Test PDF file missing"

    parser = PDFParser()
    assert parser.can_parse(pdf_path) is True

    docs = parser.parse(pdf_path)
    assert len(docs) == 3, f"Expected 3 pages, got {len(docs)}"

    # Page 1
    p1 = docs[0]
    assert p1.page == 1
    assert p1.source_type == "pdf"
    assert "loan_policy_handbook.pdf" in p1.source
    assert "Operating History" in p1.raw_content
    assert "6 months" in p1.raw_content

    # Page 2: Leverage Table
    p2 = docs[1]
    assert p2.page == 2
    assert "Leverage" in p2.title or "Section 2" in p2.title
    assert "Revenue" in p2.raw_content

    # Page 3: Restricted Industries
    p3 = docs[2]
    assert p3.page == 3
    assert "Restricted" in p3.title or "Section 3" in p3.title
    assert "Gambling" in p3.raw_content or "Cryptocurrency" in p3.raw_content


def test_html_parser_extraction():
    """Validates HTML parsing with BeautifulSoup4, table parsing, and noise removal."""
    html_path = RAW_DIR / "equipment_financing_portal.html"
    assert html_path.exists(), "Test HTML file missing"

    parser = HTMLParser()
    assert parser.can_parse(html_path) is True

    docs = parser.parse(html_path)
    assert len(docs) >= 1

    # Verify noise was stripped
    for d in docs:
        assert "We use cookies" not in d.raw_content
        assert "<nav>" not in d.raw_content
        assert "<script>" not in d.raw_content

    # Verify table extracted in section 2
    table_docs = [d for d in docs if len(d.tables) > 0]
    assert len(table_docs) >= 1
    t = table_docs[0].tables[0]
    assert "Max Amount" in t.headers or "Equipment Category" in t.headers
    assert len(t.rows) >= 3


def test_table_parser_csv():
    """Validates CSV parsing, structured TableData extraction, and markdown representation."""
    csv_path = RAW_DIR / "commercial_rate_sheet.csv"
    assert csv_path.exists(), "Test CSV file missing"

    parser = TableParser()
    assert parser.can_parse(csv_path) is True

    docs = parser.parse(csv_path)
    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_type == "csv"
    assert len(doc.tables) == 1
    assert doc.tables[0].row_count == 4
    assert "tier_name" in doc.tables[0].headers
    assert "Prime Commercial" in doc.raw_content
    assert "5.99%" in doc.raw_content


def test_text_parser_markdown_headings():
    """Validates plain text / markdown section detection and chunking."""
    txt_path = RAW_DIR / "faq_and_objections.txt"
    assert txt_path.exists(), "Test TXT file missing"

    parser = TextParser()
    assert parser.can_parse(txt_path) is True

    docs = parser.parse(txt_path)
    assert len(docs) == 5

    titles = [d.title for d in docs]
    assert any("Prepayment" in t for t in titles)
    assert any("Funding" in t for t in titles)
    assert any("Credit" in t for t in titles)
    assert any("Objection" in t for t in titles)


def test_laya_classification():
    """Validates Laya System 1 decision model content classification."""
    # Qualification text
    cat_qual, conf_qual = laya_classifier.classify_content(
        "Minimum time in business: 6 months of active operations required. Monthly revenue must be at least $10,000."
    )
    assert cat_qual == "qualification"
    assert conf_qual > 0.0

    # Product text
    cat_prod, conf_prod = laya_classifier.classify_content(
        "Commercial Term Loan: $25,000 to $500,000 with 12 to 60 months repayment terms at 6.99% APR."
    )
    assert cat_prod == "product"

    # FAQ text
    cat_faq, conf_faq = laya_classifier.classify_content(
        "Question: How fast can I get funded? Answer: Approvals are provided in 2 to 4 hours."
    )
    assert cat_faq == "faq"

    # Objection text
    cat_obj, conf_obj = laya_classifier.classify_content(
        "Objection: I am hesitant because your interest rates are too high and brokers have scammed me."
    )
    assert cat_obj == "objection"


def test_langgraph_ingestion_workflow_e2e():
    """Validates full LangGraph StateGraph execution from START to END."""
    # Ingest PDF
    res_pdf = ingest_file(str(RAW_DIR / "loan_policy_handbook.pdf"))
    assert res_pdf["source_type"] == "pdf"
    assert res_pdf["selected_parser"] == "pdf"
    assert res_pdf["validation_status"] == "valid"
    assert res_pdf["flagged_for_manual_review"] is False
    assert len(res_pdf["extracted_documents"]) == 3
    assert res_pdf["stored_path"] is not None

    # Verify JSON output structure
    doc = res_pdf["extracted_documents"][0]
    assert doc.document_id.startswith("doc_")
    assert doc.source == "loan_policy_handbook.pdf"
    assert doc.page == 1
    assert doc.title != ""
    assert doc.content_type in ["qualification", "policy", "product", "faq"]
    assert doc.extraction_status == "success"


def test_langgraph_conditional_error_and_review_branch():
    """
    Validates conditional branching for extraction failure:
    Extraction failed -> Retry alternate parser -> Still failed -> Flag for manual review.
    """
    corrupt_path = RAW_DIR / "corrupted_archive.dat"
    res = ingest_file(str(corrupt_path))

    assert res["flagged_for_manual_review"] is True
    assert len(res["extracted_documents"]) == 1
    flagged_doc = res["extracted_documents"][0]
    assert flagged_doc.extraction_status == "flagged_for_review"
    assert flagged_doc.metadata.get("flagged_for_manual_review") is True
