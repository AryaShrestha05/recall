"""Run ingestion in a background thread and track its progress in PostgreSQL."""

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .db import connect
from .ingest import ingest

log = logging.getLogger(__name__)

# One worker: Whisper already uses the whole CPU/GPU, so running two
# transcriptions at once would only make both slower. Extra uploads wait
# in the queue with status "queued".
_executor: ThreadPoolExecutor | None = None

JOB_COLUMNS = "id, status, memory_id, error, created_at, updated_at"


def create_job(audio_path: Path) -> dict:
    """Record a new queued job for an already-saved recording."""
    with connect() as conn:
        return conn.execute(
            f"INSERT INTO ingest_jobs (audio_path) VALUES (%s) RETURNING {JOB_COLUMNS}",
            (str(audio_path),),
        ).fetchone()


def get_job(job_id: int) -> dict:
    with connect() as conn:
        row = conn.execute(
            f"SELECT {JOB_COLUMNS} FROM ingest_jobs WHERE id = %s", (job_id,)
        ).fetchone()
    if not row:
        raise KeyError(job_id)
    return row


def submit(job_id: int) -> None:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingest")
    _executor.submit(run_job, job_id)


def shutdown() -> None:
    """Stop accepting work. A transcription already in progress still finishes."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
        _executor = None


def run_job(job_id: int) -> None:
    with connect() as conn:
        row = conn.execute(
            "UPDATE ingest_jobs SET status = 'running', updated_at = NOW()"
            " WHERE id = %s AND status = 'queued' RETURNING audio_path",
            (job_id,),
        ).fetchone()
    if not row:
        return

    try:
        memory_id = ingest(Path(row["audio_path"]))
    except Exception as exc:
        log.exception("ingest job %s failed", job_id)
        _finish(job_id, "failed", error=f"{type(exc).__name__}: {exc}")
    else:
        _finish(job_id, "done", memory_id=memory_id)


def fail_interrupted_jobs() -> None:
    """Mark jobs left unfinished by a previous server process as failed.

    Jobs live in this process's memory, so after a restart nothing will ever
    pick them up again. Assumes a single server process.
    """
    with connect() as conn:
        conn.execute(
            "UPDATE ingest_jobs"
            " SET status = 'failed', error = 'server restarted before the job finished',"
            " updated_at = NOW()"
            " WHERE status IN ('queued', 'running')"
        )


def _finish(job_id: int, status: str, memory_id: int | None = None, error: str | None = None):
    with connect() as conn:
        conn.execute(
            "UPDATE ingest_jobs SET status = %s, memory_id = %s, error = %s, updated_at = NOW()"
            " WHERE id = %s",
            (status, memory_id, error, job_id),
        )
