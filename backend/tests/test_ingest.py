"""Ingest safety tests. Uses a fake transcriber and database, so no Whisper or PostgreSQL is needed."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import app as app_module
from backend import ingest as ingest_module


class FakeConnection:
    """Just enough of a psycopg connection for ingest(); records inserted sources."""

    def __init__(self, store, fail=False):
        self.store = store
        self.fail = fail

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params):
        if self.fail:
            raise RuntimeError("database down")
        if "INSERT INTO sources" in sql:
            self.store["sources"].append(params)
        else:
            self.store["memories"].append(params)
        return self

    def fetchone(self):
        return {"id": len(self.store["sources"])}

    def cursor(self):
        return self

    def executemany(self, sql, rows):
        pass


@pytest.fixture
def env(tmp_path, monkeypatch):
    sources = tmp_path / "data" / "sources"
    store = {"sources": [], "memories": [], "fail_db": False}
    monkeypatch.setattr(ingest_module, "SOURCES", sources)
    monkeypatch.setattr(
        ingest_module,
        "transcribe",
        lambda path: {"text": "hello", "segments": [{"start": 0.0, "end": 1.0, "text": "hello"}]},
    )
    monkeypatch.setattr(ingest_module, "connect", lambda: FakeConnection(store, store["fail_db"]))
    monkeypatch.setattr(app_module, "get_memory", lambda mid: {"id": mid})
    return sources, store


def upload(name, data=b"audio"):
    return TestClient(app_module.app).post("/ingest", files={"file": (name, data)})


def test_same_filename_uploads_never_overwrite(env):
    sources, store = env
    assert upload("recording.m4a", b"first").status_code == 200
    assert upload("recording.m4a", b"second").status_code == 200

    files = sorted(sources.iterdir())
    assert len(files) == 2
    assert {f.read_bytes() for f in files} == {b"first", b"second"}
    assert all(f.suffix == ".m4a" and f.stem != "recording" for f in files)
    assert {s[1] for s in store["sources"]} == {str(f) for f in files}
    assert [m[0] for m in store["memories"]] == ["recording", "recording"]


@pytest.mark.parametrize("name", ["../../escape.m4a", "/tmp/escape.m4a", "..\\..\\escape.m4a", ".."])
def test_upload_name_cannot_escape_sources(env, name):
    sources, store = env
    assert upload(name).status_code == 200

    stored = [s[1] for s in store["sources"]]
    assert stored == [str(f) for f in sources.iterdir()]
    assert all(Path(p).resolve().parent == sources.resolve() for p in stored)


def test_unsafe_extension_is_dropped(env):
    sources, _ = env
    upload("clip.m4a/../../x")
    upload("clip.$(rm)")
    assert [f.suffix for f in sources.iterdir()] == ["", ""]


def test_failed_transcription_removes_stored_audio(env, monkeypatch):
    sources, store = env

    def broken(path):
        raise RuntimeError("whisper crashed")

    monkeypatch.setattr(ingest_module, "transcribe", broken)
    with pytest.raises(RuntimeError):
        upload("recording.m4a")
    assert list(sources.iterdir()) == []
    assert store["sources"] == []


def test_failed_database_write_removes_stored_audio(env, tmp_path):
    sources, store = env
    store["fail_db"] = True
    original = tmp_path / "talk.mp3"
    original.write_bytes(b"audio")

    with pytest.raises(RuntimeError):
        ingest_module.ingest(original)
    assert list(sources.iterdir()) == []
    assert original.read_bytes() == b"audio"


def test_cli_ingest_copies_under_unique_name(env, tmp_path):
    sources, store = env
    original = tmp_path / "talk.mp3"
    original.write_bytes(b"audio")

    ingest_module.ingest(original)
    ingest_module.ingest(original)

    files = list(sources.iterdir())
    assert len(files) == 2 and all(f.suffix == ".mp3" for f in files)
    assert [m[0] for m in store["memories"]] == ["talk", "talk"]
