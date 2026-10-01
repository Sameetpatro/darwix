import pytest
from app.kb.loader import load_knowledge_base
from app.kb.retriever import KnowledgeRetriever, STRICT_FALLBACK_TEXT
from app.qualification.models import LoanApplication
from app.qualification.dialog_manager import DialogManager


def test_kb_loader_chunks():
    chunks = load_knowledge_base()
    assert len(chunks) >= 10
    categories = {c.category for c in chunks}
    assert "loan_products" in categories
    assert "eligibility_and_policies" in categories
    assert "faqs" in categories
    assert "rates_and_terms" in categories


def test_kb_product_retrieval():
    retriever = KnowledgeRetriever()

    # Equipment Financing
    res1 = retriever.query_with_fallback("Tell me about your equipment financing program.")
    assert res1.has_match is True
    assert "equipment" in res1.voice_answer.lower() or "1,000,000" in res1.voice_answer
    assert "loan_products.md" in (res1.citation or "")

    # Line of Credit
    res2 = retriever.query_with_fallback("What is your revolving line of credit limit?")
    assert res2.has_match is True
    assert "revolving" in res2.voice_answer.lower() or "line-of-credit" in (res2.citation or "")


def test_kb_faqs_retrieval():
    retriever = KnowledgeRetriever()

    # Prepayment Penalty FAQ
    res_prepay = retriever.query_with_fallback("Are there any prepayment penalties if I pay off early?")
    assert res_prepay.has_match is True
    assert "zero prepayment penalties" in res_prepay.voice_answer.lower() or "no prepayment" in res_prepay.voice_answer.lower()
    assert "faq-prepayment-penalty" in (res_prepay.citation or "")

    # Document Requirements FAQ
    res_docs = retriever.query_with_fallback("What paperwork and bank statements do I need to submit?")
    assert res_docs.has_match is True
    assert "bank statements" in res_docs.voice_answer.lower()
    assert "faq-required-documents" in (res_docs.citation or "")

    # Funding Timeline FAQ
    res_speed = retriever.query_with_fallback("How fast can I get funded?")
    assert res_speed.has_match is True
    assert "24" in res_speed.voice_answer or "48" in res_speed.voice_answer


def test_kb_strict_fallback_and_non_hallucination():
    retriever = KnowledgeRetriever()

    # Out-of-scope query
    res_out = retriever.query_with_fallback("What is the capital of Australia and what's the weather?")
    assert res_out.has_match is False
    assert res_out.voice_answer == STRICT_FALLBACK_TEXT
    assert res_out.citation is None

    # Unrelated crypto inquiry
    res_crypto = retriever.query_with_fallback("Can I use this loan to trade cryptocurrency and bitcoin tokens?")
    assert res_crypto.has_match is False
    assert res_crypto.voice_answer == STRICT_FALLBACK_TEXT


def test_dialog_manager_kb_integration():
    dm = DialogManager()
    app = LoanApplication()

    # Caller asks a valid KB question during dialogue
    reply, meta = dm.process_turn(app, "Do you have prepayment penalties if I pay early?", 1)
    assert meta["action"] == "kb_and_ask_field"
    assert "Darwix KB" in (meta.get("kb_citation") or "")
    assert "prepayment" in reply.lower()
    # Confirms it also asks the next missing qualification question
    assert "name" in reply.lower()


def test_dialog_manager_out_of_scope_fallback():
    dm = DialogManager()
    app = LoanApplication()

    # Caller asks an out-of-scope question
    reply, meta = dm.process_turn(app, "Can you tell me how to invest in cryptocurrency futures?", 1)
    assert meta["action"] == "kb_fallback"
    assert reply == STRICT_FALLBACK_TEXT
    assert meta.get("citation") is None
