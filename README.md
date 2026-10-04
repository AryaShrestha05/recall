# Recall

Personal memory system. Record or upload audio, then turn it into structured, searchable knowledge.

The transcript is raw material. The product is the memory layer on top of it.

**Loop:** Experience → Capture → Understand → Structure → Connect → Retrieve

## Status

Working now: **audio in → stored source → transcript with timestamps**.

Not built yet: extraction (summary, people, topics, actions), Memory UI, embeddings / Ask, Expo app, Supabase.

PostgreSQL stores memories and transcripts. Raw audio is never overwritten.

## Requirements

- macOS on Apple Silicon for local MLX transcription
- Python 3.12
- [ffmpeg](https://ffmpeg.org/) (`brew install ffmpeg`)
- PostgreSQL 17

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
```

Create the database once and apply the first migration:

```bash
createuser recall
createdb -O recall recall
psql postgresql://recall@localhost:5432/recall -f supabase/migrations/20260927000000_initial.sql
psql postgresql://recall@localhost:5432/recall -f supabase/migrations/20261001000000_ingest_jobs.sql
```

Tell Recall which PostgreSQL database to use:

```bash
export DATABASE_URL=postgresql://recall@localhost:5432/recall
export TRANSCRIPTION_ENGINE=mlx
```

## Ingest a recording

Copies the file into `data/sources/` under a new random name (the original filename becomes the memory title), transcribes it, and writes a Memory plus timestamped segments to PostgreSQL. If transcription or the database write fails, the copied file is removed.

```bash
python -m backend.ingest path/to/recording.m4a
```

First run downloads the Whisper small model. Re-running ingest on the same file creates a new memory; it does not replace the previous one.

## API

From the repo root:

```bash
uvicorn backend.app:app --reload
```

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/memories` | List the 50 newest memories for Home |
| `POST` | `/ingest` | Upload an audio file and queue it for transcription. Returns `202` and a job |
| `GET` | `/jobs/{id}` | Job status: `queued` → `running` → `done` (with `memory_id`) or `failed` (with `error`) |
| `GET` | `/memories/{id}` | Source + full transcript + segments |

Transcription runs in a background thread, one recording at a time, so the server keeps answering other requests while Whisper works. Upload, then poll the job until it is `done`:

```bash
curl -F "file=@recording.m4a" http://127.0.0.1:8000/ingest
# {"id": 1, "status": "queued", "memory_id": null, ...}
curl http://127.0.0.1:8000/jobs/1
# {"id": 1, "status": "done", "memory_id": 1, ...}
curl http://127.0.0.1:8000/memories/1
```

Jobs run inside the server process. If the server stops mid-transcription, unfinished jobs are marked `failed` on the next start and their audio is deleted, the same as any failed ingest; upload the file again. Run a single server process (the default for `uvicorn`).

Docs: http://127.0.0.1:8000/docs

## Tests and linting

There are two test suites, both using a fake transcriber so Whisper is never loaded:

- `backend/tests/` checks upload safety (unique stored names, path traversal, cleanup on failure) with a fake database, so it needs no PostgreSQL.
- `tests/` runs the full pipeline and API against a real, disposable PostgreSQL database. Every run wipes and rebuilds its tables, so it only uses `TEST_DATABASE_URL` and refuses to start without it; it never touches `DATABASE_URL`.

```bash
pip install -r backend/requirements-test.txt
python -m pytest backend/tests          # no database needed

createdb -O recall recall_test
export TEST_DATABASE_URL=postgresql://recall@localhost:5432/recall_test
pytest                                  # both suites
ruff check .
ruff format .
```

GitHub Actions (`.github/workflows/ci.yml`) runs ruff and both suites against a temporary PostgreSQL 17 on every push to `main` and every pull request.

Dependency versions are pinned with `==` in `backend/requirements*.txt`. To upgrade one, change its version, rerun the tests, and commit.

## Layout

```
backend/app.py      FastAPI routes
backend/db.py       PostgreSQL connection and memory fetch
backend/ingest.py   Copy audio and persist the result
backend/jobs.py     Background ingest queue and job status
backend/transcription.py Shared development/production transcription entry point
supabase/migrations PostgreSQL schema changes used locally and in Supabase
tests/              pytest suite (fake transcriber, disposable database)
data/sources/       Raw audio (gitignored)
```

Production installs `backend/requirements-production.txt` and sets:

```bash
export TRANSCRIPTION_ENGINE=faster-whisper
```

## Next

1. Extract summary, people, topics, actions, decisions from a memory (with source quotes)
2. Memory page
3. Chunk + embed + “Ask this memory”
4. Expo record/upload into the same ingest path
