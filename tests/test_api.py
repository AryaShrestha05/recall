from pathlib import Path


def test_memories_starts_empty(client):
    response = client.get("/memories")

    assert response.status_code == 200
    assert response.json() == []


def test_ingest_upload_returns_the_new_memory(client, sources_dir):
    response = client.post("/ingest", files={"file": ("talk.m4a", b"audio bytes", "audio/mp4")})

    assert response.status_code == 200
    memory = response.json()
    assert memory["title"] == "talk"
    assert len(memory["segments"]) == 2
    stored = Path(memory["raw_uri"])
    assert stored.parent == sources_dir
    assert stored.read_bytes() == b"audio bytes"


def test_memory_list_and_detail_after_upload(client):
    memory_id = client.post("/ingest", files={"file": ("talk.m4a", b"audio")}).json()["id"]

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
