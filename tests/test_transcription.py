from pathlib import Path

import pytest

from backend.transcription import transcribe


def test_fake_engine_returns_text_and_segments():
    result = transcribe(Path("talk.m4a"))

    assert "talk.m4a" in result["text"]
    assert [s["start"] for s in result["segments"]] == [0.0, 2.5]
    assert all(s["end"] >= s["start"] for s in result["segments"])


def test_unknown_engine_is_rejected(monkeypatch):
    monkeypatch.setenv("TRANSCRIPTION_ENGINE", "nope")

    with pytest.raises(RuntimeError, match="Unknown TRANSCRIPTION_ENGINE"):
        transcribe(Path("talk.m4a"))
