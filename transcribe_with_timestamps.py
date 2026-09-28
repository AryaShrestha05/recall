"""Transcribe one recording and print each piece with its time."""

import sys
from pathlib import Path

import mlx_whisper


if len(sys.argv) != 2:
    raise SystemExit("Usage: python transcribe_with_timestamps.py <audio-file>")

audio_file = Path(sys.argv[1])

if not audio_file.is_file():
    raise SystemExit(f"Audio file not found: {audio_file}")

# Whisper returns a complete transcript plus a list named "segments".
result = mlx_whisper.transcribe(
    str(audio_file),
    path_or_hf_repo="mlx-community/whisper-small-mlx",
)

# A segment is a short piece of speech with a start time, end time, and text.
for segment in result["segments"]:
    start = segment["start"]
    end = segment["end"]
    text = segment["text"].strip()

    # :.1f displays seconds with one digit after the decimal point.
    print(f"[{start:.1f}s - {end:.1f}s] {text}")
