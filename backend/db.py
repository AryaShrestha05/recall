"""PostgreSQL connection and database reads for Recall."""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SOURCES = DATA / "sources"

# Load the real local configuration from /recall/.env.
# Production supplies the same names through its hosting environment.
load_dotenv(ROOT / ".env")


def connect() -> psycopg.Connection:
    """Open a connection to the PostgreSQL database in DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(database_url, row_factory=dict_row)


def list_memories() -> list[dict]:
    """Return the newest memories for the Home screen."""
    with connect() as conn:
        return conn.execute(
            """
            SELECT m.id, m.title, m.type, m.created_at, m.summary,
                   s.duration
            FROM memories m
            JOIN sources s ON s.id = m.source_id
            ORDER BY m.created_at DESC
            LIMIT 50
            """
        ).fetchall()


def get_memory(memory_id: int) -> dict:
    """Return one memory with its source and timestamped transcript segments."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT m.id, m.title, m.type, m.created_at, m.summary,
                   s.id AS source_id, s.type AS source_type, s.raw_uri, s.transcript, s.duration
            FROM memories m JOIN sources s ON s.id = m.source_id
            WHERE m.id = %s
            """,
            (memory_id,),
        ).fetchone()
        if not row:
            raise KeyError(memory_id)
        segs = conn.execute(
            """
            SELECT start_time, end_time, text
            FROM transcript_segments
            WHERE memory_id = %s
            ORDER BY start_time
            """,
            (memory_id,),
        ).fetchall()
        return {**row, "segments": segs}
