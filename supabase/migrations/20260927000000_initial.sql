-- The first Recall schema: recording, memory, and timestamped transcript.

CREATE TABLE sources (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('audio', 'text')),
    raw_uri TEXT NOT NULL,
    transcript TEXT,
    duration DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id BIGINT NOT NULL UNIQUE REFERENCES sources(id),
    title TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('lecture', 'meeting', 'conversation', 'voice_note', 'thought')),
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE transcript_segments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    memory_id BIGINT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    start_time DOUBLE PRECISION NOT NULL,
    end_time DOUBLE PRECISION NOT NULL,
    text TEXT NOT NULL,
    CHECK (start_time >= 0),
    CHECK (end_time >= start_time)
);

CREATE INDEX transcript_segments_memory_time
    ON transcript_segments (memory_id, start_time);
