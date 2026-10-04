import threading
import time
from pathlib import Path

import backend.ingest
from backend import jobs


def wait_for_job(client, job_id, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} still {job['status']} after {timeout}s")


def upload(client, name="talk.m4a", content=b"audio bytes"):
    response = client.post("/ingest", files={"file": (name, content, "audio/mp4")})
    assert response.status_code == 202
    return response.json()


def test_memories_starts_empty(client):
    response = client.get("/memories")

    assert response.status_code == 200
    assert response.json() == []


def test_ingest_returns_a_job_that_finishes_with_a_memory(client, sources_dir):
    job = upload(client)
    assert job["status"] == "queued"
    assert job["memory_id"] is None

    job = wait_for_job(client, job["id"])
    assert job["status"] == "done"
    assert job["error"] is None

    memory = client.get(f"/memories/{job['memory_id']}").json()
    assert memory["title"] == "talk"
    assert len(memory["segments"]) == 2
    stored = Path(memory["raw_uri"])
    assert stored.parent == sources_dir
    assert stored.read_bytes() == b"audio bytes"


def test_server_stays_responsive_while_transcribing(client, monkeypatch):
    release = threading.Event()
    real_transcribe = backend.ingest.transcribe

    def slow_transcribe(path):
        assert release.wait(5), "test never released the transcription"
        return real_transcribe(path)

    monkeypatch.setattr(backend.ingest, "transcribe", slow_transcribe)

    job = upload(client)
    assert client.get("/memories").json() == []
    assert client.get(f"/jobs/{job['id']}").json()["status"] in ("queued", "running")

    release.set()
    assert wait_for_job(client, job["id"])["status"] == "done"


def test_uploads_are_processed_in_order(client):
    first, second = upload(client, "a.m4a"), upload(client, "b.m4a")

    first, second = wait_for_job(client, first["id"]), wait_for_job(client, second["id"])
    titles = [client.get(f"/memories/{j['memory_id']}").json()["title"] for j in (first, second)]
    assert titles == ["a", "b"]


def test_failed_transcription_marks_job_failed(client, monkeypatch, sources_dir):
    def broken_transcribe(_path):
        raise RuntimeError("model crashed")

    monkeypatch.setattr(backend.ingest, "transcribe", broken_transcribe)

    job = wait_for_job(client, upload(client)["id"])
    assert job["status"] == "failed"
    assert job["error"] == "RuntimeError: model crashed"
    assert job["memory_id"] is None
    assert client.get("/memories").json() == []
    assert list(sources_dir.iterdir()) == []


def test_restart_fails_jobs_left_unfinished(client, tmp_path):
    audio = tmp_path / "lost.m4a"
    audio.write_bytes(b"audio")
    job = jobs.create_job(audio, "lost")

    jobs.fail_interrupted_jobs()

    job = client.get(f"/jobs/{job['id']}").json()
    assert job["status"] == "failed"
    assert "restarted" in job["error"]
    assert not audio.exists()


def test_memory_list_and_detail_after_upload(client):
    memory_id = wait_for_job(client, upload(client)["id"])["memory_id"]

    listed = client.get("/memories").json()
    assert [m["id"] for m in listed] == [memory_id]
    assert "transcript" not in listed[0]

    detail = client.get(f"/memories/{memory_id}").json()
    assert detail["id"] == memory_id
    assert Path(detail["raw_uri"]).name in detail["transcript"]


def test_unknown_memory_is_404(client):
    response = client.get("/memories/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "memory not found"}


def test_unknown_job_is_404(client):
    response = client.get("/jobs/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}
