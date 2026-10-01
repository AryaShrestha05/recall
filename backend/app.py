import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile

from . import jobs
from .db import SOURCES, get_memory, list_memories


@asynccontextmanager
async def lifespan(_app: FastAPI):
    jobs.fail_interrupted_jobs()
    yield
    jobs.shutdown()


app = FastAPI(title="Recall", lifespan=lifespan)


@app.get("/memories")
def read_memories():
    """Return recent memories without their large transcripts."""
    return list_memories()


@app.post("/ingest", status_code=202)
def ingest_upload(file: UploadFile = File(...)):
    """Save the upload and queue it for transcription. Poll GET /jobs/{id} for the result."""
    SOURCES.mkdir(parents=True, exist_ok=True)
    dest = SOURCES / (file.filename or "upload.m4a")
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    job = jobs.create_job(dest)
    jobs.submit(job["id"])
    return job


@app.get("/jobs/{job_id}")
def read_job(job_id: int):
    try:
        return jobs.get_job(job_id)
    except KeyError:
        raise HTTPException(404, "job not found") from None


@app.get("/memories/{memory_id}")
def read_memory(memory_id: int):
    try:
        return get_memory(memory_id)
    except KeyError:
        raise HTTPException(404, "memory not found") from None
