import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from . import jobs
from .db import get_memory, list_memories
from .ingest import new_source_path


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
    # The client's filename is only used for the title and extension, never as a path.
    original = Path(file.filename or "upload.m4a").name
    dest = new_source_path(original)
    try:
        with dest.open("xb") as out:
            shutil.copyfileobj(file.file, out)
        job = jobs.create_job(dest, Path(original).stem or "upload")
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
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
