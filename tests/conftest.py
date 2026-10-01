"""Shared test setup: a throwaway database and the fake transcription engine."""

import os
from pathlib import Path

import psycopg
import pytest

# Tests wipe every table, so they only run against a database named in
# TEST_DATABASE_URL, never the DATABASE_URL from a developer's .env file.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise pytest.UsageError(
        "Set TEST_DATABASE_URL to an empty, disposable PostgreSQL database before running tests."
    )
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["TRANSCRIPTION_ENGINE"] = "fake"

MIGRATIONS = Path(__file__).resolve().parent.parent / "supabase" / "migrations"
# This migration needs Supabase's storage schema, which plain PostgreSQL lacks.
SUPABASE_ONLY = {"20260928000000_recordings_bucket.sql"}


@pytest.fixture(scope="session", autouse=True)
def schema():
    """Rebuild the schema from the migrations once per test run."""
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            if migration.name not in SUPABASE_ONLY:
                conn.execute(migration.read_text())


@pytest.fixture(autouse=True)
def empty_tables(schema):
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE ingest_jobs, transcript_segments, memories, sources RESTART IDENTITY CASCADE"
        )


@pytest.fixture(autouse=True)
def sources_dir(tmp_path, monkeypatch):
    """Store copied recordings in a temporary folder instead of data/sources/."""
    import backend.app
    import backend.ingest

    folder = tmp_path / "sources"
    monkeypatch.setattr(backend.ingest, "SOURCES", folder)
    monkeypatch.setattr(backend.app, "SOURCES", folder)
    return folder


@pytest.fixture
def audio_file(tmp_path):
    """A stand-in recording. The fake engine never reads its contents."""
    path = tmp_path / "upload" / "lecture.m4a"
    path.parent.mkdir()
    path.write_bytes(b"not really audio")
    return path


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from backend.app import app

    with TestClient(app) as test_client:
        yield test_client
