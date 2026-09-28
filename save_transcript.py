"""Transcribe one recording and save the timestamped text to transcript.txt."""

import sys
from pathlib import Path

import mlx_whisper


if len(sys.argv) != 2:
    raise SystemExit("Usage: python save_transcript.py <audio-file>")

audio_file = Path(sys.argv[1])

if not audio_file.is_file():
    raise SystemExit(f"Audio file not found: {audio_file}")

# Turn the recording into timestamped transcript segments.
result = mlx_whisper.transcribe(
    str(audio_file),
    path_or_hf_repo="mlx-community/whisper-small-mlx",
)

# Build a list containing one readable line for every segment.
lines = []
for segment in result["segments"]:
    start = segment["start"]
    end = segment["end"]
    text = segment["text"].strip()
    lines.append(f"[{start:.1f}s - {end:.1f}s] {text}")

# Join the separate lines into one block of text.
transcript = "\n".join(lines)

# Save that text in the project folder. Existing transcript.txt is replaced.
output_file = Path("transcript.txt")
output_file.write_text(transcript, encoding="utf-8")

print(f"Transcript saved to {output_file.resolve()}")
