"""Convert audio into one transcript and timestamped segments."""

import os
from functools import cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def transcribe(audio_path: Path) -> dict:
    """Use the configured speech engine and return one consistent result shape."""
    engine = os.getenv("TRANSCRIPTION_ENGINE", "mlx")

    if engine == "mlx":
        return _transcribe_with_mlx(audio_path)
    if engine == "faster-whisper":
        return _transcribe_with_faster_whisper(audio_path)

    raise RuntimeError(
        f"Unknown TRANSCRIPTION_ENGINE: {engine}. Use 'mlx' or 'faster-whisper'."
    )


def _transcribe_with_mlx(audio_path: Path) -> dict:
    """Run Whisper locally on an Apple Silicon development Mac."""
    import mlx_whisper

    result = mlx_whisper.transcribe(
        str(audio_path),
        path_or_hf_repo="mlx-community/whisper-small-mlx",
    )

    return {
        "text": (result.get("text") or "").strip(),
        "segments": result.get("segments") or [],
    }


def _transcribe_with_faster_whisper(audio_path: Path) -> dict:
    """Run Whisper on the Linux production worker without a per-minute API."""
    model_name = os.getenv("WHISPER_MODEL", "small")
    model = _get_faster_whisper_model(model_name)
    generated_segments, _ = model.transcribe(str(audio_path))

    # faster-whisper returns a generator, so consume it once and convert each
    # object into the same dictionary shape returned by mlx-whisper.
    segments = [
        {"start": segment.start, "end": segment.end, "text": segment.text}
        for segment in generated_segments
    ]

    return {
        "text": " ".join(segment["text"].strip() for segment in segments),
        "segments": segments,
    }


@cache
def _get_faster_whisper_model(model_name: str):
    """Load each production model once, then reuse it for later recordings."""
    from faster_whisper import WhisperModel

    return WhisperModel(model_name, compute_type="int8")
