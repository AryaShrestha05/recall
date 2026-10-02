"""Turn one audio recording into text.

Run it like this:
    .venv/bin/python transcribe.py path/to/recording.m4a
"""

# sys lets this script read the audio path typed after "transcribe.py".
import sys

# Path gives us a convenient way to check whether that audio file exists.
from pathlib import Path

# mlx_whisper is the speech-to-text tool that listens to the recording.
import mlx_whisper

# The command must contain exactly one audio path.
if len(sys.argv) != 2:
    raise SystemExit("Usage: python transcribe.py <audio-file>")

# sys.argv[1] is the audio path supplied by the person running the command.
audio_file = Path(sys.argv[1])

# Give a clear error instead of asking Whisper to open a missing file.
if not audio_file.is_file():
    raise SystemExit(f"Audio file not found: {audio_file}")

# Whisper listens to the audio and returns a dictionary containing its result.
result = mlx_whisper.transcribe(
    str(audio_file),
    path_or_hf_repo="mlx-community/whisper-small-mlx",
)

# The "text" item contains the complete transcript.
transcript = result["text"]

# Show the transcript in the terminal.
print(transcript)
