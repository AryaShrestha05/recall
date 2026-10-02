import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from .db import get_memory, list_memories
from .ingest import ingest_stored, new_source_path

app = FastAPI(title="Recall")


@app.get("/memories")
def read_memories():
    """Return recent memories without their large transcripts."""
    return list_memories()


@app.post("/ingest")
def ingest_upload(file: UploadFile = File(...)):
    # The client's filename is only used for the title and extension, never as a path.
    original = Path(file.filename or "upload.m4a").name
    dest = new_source_path(original)
    try:
        with dest.open("xb") as out:
            shutil.copyfileobj(file.file, out)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return get_memory(ingest_stored(dest, Path(original).stem or "upload"))


@app.get("/memories/{memory_id}")
def read_memory(memory_id: int):
    try:
        return get_memory(memory_id)
    except KeyError:
        raise HTTPException(404, "memory not found")
