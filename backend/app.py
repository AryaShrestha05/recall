from fastapi import FastAPI, File, HTTPException, UploadFile

from .db import SOURCES, get_memory, list_memories
from .ingest import ingest

app = FastAPI(title="Recall")


@app.get("/memories")
def read_memories():
    """Return recent memories without their large transcripts."""
    return list_memories()


@app.post("/ingest")
async def ingest_upload(file: UploadFile = File(...)):
    SOURCES.mkdir(parents=True, exist_ok=True)
    dest = SOURCES / (file.filename or "upload.m4a")
    dest.write_bytes(await file.read())
    return get_memory(ingest(dest))


@app.get("/memories/{memory_id}")
def read_memory(memory_id: int):
    try:
        return get_memory(memory_id)
    except KeyError:
        raise HTTPException(404, "memory not found")
