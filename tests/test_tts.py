import os
from pathlib import Path
import pytest
from app.tts.edge_tts_engine import TTSEngine


@pytest.mark.asyncio
async def test_tts_engine_synthesis():
    engine = TTSEngine()
    url, path, latency = await engine.synthesize(
        text="Welcome to Darwix. This is a voice test.",
        call_id="unit_test_call",
        turn_id=1,
    )

    assert url.startswith("/recordings/")
    assert Path(path).exists()
    assert Path(path).stat().st_size > 0
    assert latency > 0

    # Cleanup test file
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass
