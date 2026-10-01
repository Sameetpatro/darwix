import pytest
from app.llm.deepseek import clean_text_for_speech, DeepSeekClient
from app.llm.mock_fallback import generate_fallback_response


def test_clean_text_for_speech():
    raw = "**Hello!** Here is a *list* of options:\n* Option 1\n* Option 2\n# Header\n`code`"
    cleaned = clean_text_for_speech(raw)
    assert "*" not in cleaned
    assert "#" not in cleaned
    assert "`" not in cleaned
    assert "Hello! Here is a list of options" in cleaned


def test_fallback_dialog_generator():
    reply_hello = generate_fallback_response([{"role": "user", "content": "Hi there"}])
    assert len(reply_hello) > 0
    assert "Vani" in reply_hello or "Darwix" in reply_hello or "financing" in reply_hello

    reply_loan = generate_fallback_response([{"role": "user", "content": "I need a loan for working capital"}])
    assert len(reply_loan) > 0


@pytest.mark.asyncio
async def test_deepseek_client_error_resilience():
    client = DeepSeekClient()
    # Test that generate_response returns clean speech text even if DeepSeek balance is 0 or key fails
    text, latency, provider = await client.generate_response(
        messages=[{"role": "user", "content": "Hello Vani"}]
    )
    assert len(text) > 0
    assert latency > 0
    assert provider in ("deepseek", "fallback_agent", "deepseek_fallback_balance_exhausted", "deepseek_fallback_exception")
