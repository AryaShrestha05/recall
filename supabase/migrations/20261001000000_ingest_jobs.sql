-- One row per uploaded recording waiting for, undergoing, or finished with
-- background transcription. Clients poll it after POST /ingest.

CREATE TABLE ingest_jobs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'done', 'failed')),
    audio_path TEXT NOT NULL,
    title TEXT NOT NULL,
    memory_id BIGINT REFERENCES memories(id) ON DELETE SET NULL,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (status <> 'done' OR memory_id IS NOT NULL)
);
