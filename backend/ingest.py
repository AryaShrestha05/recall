from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from .db import SOURCES, connect
from .transcription import transcribe


def ingest(audio_path: Path, title: str | None = None) -> int:
    """Turn one audio file into a stored memory and return its database ID."""

    # Convert paths such as "./recording.m4a" into a complete absolute path.
    audio_path = audio_path.resolve()

    # Stop immediately if the caller gave us a missing file or a folder.
    if not audio_path.is_file():
        raise FileNotFoundError(audio_path)

    # Keep a copy of the original recording inside Recall's source directory.
    SOURCES.mkdir(parents=True, exist_ok=True)
    stored = SOURCES / audio_path.name
    if audio_path != stored:
        shutil.copy2(audio_path, stored)

    # The selected engine returns both the full transcript and timestamped pieces.
    result = transcribe(stored)
    transcript = (result.get("text") or "").strip()
    segments = result.get("segments") or []

    # The ending time of the last piece is the recording's duration.
    duration = float(segments[-1]["end"]) if segments else None

    # Save everything in one PostgreSQL transaction. If an insert fails,
    # PostgreSQL rolls back the whole transaction instead of saving half a memory.
    with connect() as conn:
        # The source row describes the original recording and raw transcript.
        source = conn.execute(
            """
            INSERT INTO sources (type, raw_uri, transcript, duration)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            ("audio", str(stored), transcript, duration),
        ).fetchone()
        source_id = source["id"]

        # The memory row is the user-facing object built from that source.
        memory = conn.execute(
            """
            INSERT INTO memories (title, type, created_at, summary, source_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                title or audio_path.stem,
                "lecture",
                datetime.now(UTC).isoformat(),
                None,
                source_id,
            ),
        ).fetchone()
        memory_id = memory["id"]

        # Store each timestamped piece so answers can cite the exact moment.
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO transcript_segments (memory_id, start_time, end_time, text)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    (memory_id, float(s["start"]), float(s["end"]), (s.get("text") or "").strip())
                    for s in segments
                    if (s.get("text") or "").strip()
                ],
            )

    return memory_id


if __name__ == "__main__":
    # Python runs this section only for:
    #     python -m backend.ingest path/to/recording.m4a
    # Importing ingest() from the API does not run this section.
    import json
    import sys

    from .db import get_memory

    # Command-line arguments look like:
    # [".../backend/ingest.py", "path/to/recording.m4a"]
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m backend.ingest <audio>")

    # sys.argv[1] is the recording path supplied after backend.ingest.
    mid = ingest(Path(sys.argv[1]))

    # Read the saved memory back to confirm that ingestion produced a transcript.
    payload = get_memory(mid)
    assert payload["transcript"] and len(payload["transcript"]) > 50

    # Print a small result for the person running the command.
    print(
        json.dumps(
            {"memory_id": mid, "duration": payload["duration"], "chars": len(payload["transcript"])}
        )
    )
