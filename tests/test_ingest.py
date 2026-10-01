import psycopg
import pytest

import backend.ingest
from backend.db import connect, get_memory
from backend.ingest import ingest


def test_ingest_stores_source_memory_and_segments(audio_file, sources_dir):
    memory_id = ingest(audio_file)

    memory = get_memory(memory_id)
    assert memory["title"] == "lecture"
    assert memory["type"] == "lecture"
    assert memory["source_type"] == "audio"
    assert memory["duration"] == 5.0
    assert "lecture.m4a" in memory["transcript"]
    assert [s["start_time"] for s in memory["segments"]] == [0.0, 2.5]
    assert memory["segments"][0]["text"] == "This is a fake transcript of lecture.m4a."
    assert (sources_dir / "lecture.m4a").read_bytes() == b"not really audio"


def test_ingest_uses_given_title(audio_file):
    assert get_memory(ingest(audio_file, title="Biology 101"))["title"] == "Biology 101"


def test_ingest_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest(tmp_path / "missing.m4a")


def test_ingest_skips_blank_segments(audio_file, monkeypatch):
    def transcribe(_path):
        return {
            "text": "Hello",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": " Hello "},
                {"start": 1.0, "end": 2.0, "text": "   "},
            ],
        }

    monkeypatch.setattr(backend.ingest, "transcribe", transcribe)

    memory = get_memory(ingest(audio_file))
    assert [s["text"] for s in memory["segments"]] == ["Hello"]
    assert memory["duration"] == 2.0


def test_empty_transcript_has_no_duration(audio_file, monkeypatch):
    monkeypatch.setattr(backend.ingest, "transcribe", lambda _path: {"text": "", "segments": []})

    memory = get_memory(ingest(audio_file))
    assert memory["transcript"] == ""
    assert memory["duration"] is None
    assert memory["segments"] == []


def test_get_memory_raises_for_unknown_id():
    with pytest.raises(KeyError):
        get_memory(999)


def test_schema_rejects_segment_ending_before_it_starts(audio_file):
    memory_id = ingest(audio_file)

    with pytest.raises(psycopg.errors.CheckViolation), connect() as conn:
        conn.execute(
            "INSERT INTO transcript_segments (memory_id, start_time, end_time, text)"
            " VALUES (%s, 5, 1, 'backwards')",
            (memory_id,),
        )
