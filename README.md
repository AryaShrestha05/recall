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
```

Tell Recall which PostgreSQL database to use:

```bash
export DATABASE_URL=postgresql://recall@localhost:5432/recall
export TRANSCRIPTION_ENGINE=mlx
```

## Ingest a recording

Copies the file into `data/sources/`, transcribes it, and writes a Memory plus timestamped segments to PostgreSQL.

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
| `POST` | `/ingest` | Upload an audio file, transcribe, return the memory |
| `GET` | `/memories/{id}` | Source + full transcript + segments |

Example:

```bash
curl -F "file=@recording.m4a" http://127.0.0.1:8000/ingest
curl http://127.0.0.1:8000/memories/1
```

Docs: http://127.0.0.1:8000/docs

## Layout

```
backend/app.py      FastAPI routes
backend/db.py       PostgreSQL connection and memory fetch
backend/ingest.py   Copy audio and persist the result
backend/transcription.py Shared development/production transcription entry point
supabase/migrations PostgreSQL schema changes used locally and in Supabase
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
