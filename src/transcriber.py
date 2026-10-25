from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from openai import OpenAI


@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float


@dataclass
class Transcript:
    full_text: str
    segments: List[TranscriptSegment]
    language: str


def transcribe_audio(audio_path: Path, api_key: str) -> Transcript:
    """Transcribe audio using OpenAI Whisper API with segment-level timestamps."""
    client = OpenAI(api_key=api_key)

    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments: List[TranscriptSegment] = []
    for seg in (response.segments or []):
        segments.append(
            TranscriptSegment(
                text=seg.text.strip(),
                start=float(seg.start),
                end=float(seg.end),
            )
        )

    return Transcript(
        full_text=response.text,
        segments=segments,
        language=response.language or "en",
    )


def transcribe_audio_local(audio_path: Path, model_size: str = "medium") -> Transcript:
    """
    Transcribe audio locally using faster-whisper — no API key required.

    model_size options (speed vs accuracy):
      tiny    ~1 GB RAM  — fastest, least accurate
      base    ~1 GB RAM  — fast
      small   ~2 GB RAM  — good balance
      medium  ~5 GB RAM  — very good  (recommended)
      large-v3 ~10 GB RAM — best quality
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper is not installed.\n"
            "Install it with: pip install faster-whisper"
        )

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    raw_segments, info = model.transcribe(str(audio_path), beam_size=5)

    segments: List[TranscriptSegment] = []
    full_parts: List[str] = []

    for seg in raw_segments:
        text = seg.text.strip()
        if text:
            segments.append(TranscriptSegment(text=text, start=seg.start, end=seg.end))
            full_parts.append(text)

    return Transcript(
        full_text=" ".join(full_parts),
        segments=segments,
        language=info.language or "en",
    )
