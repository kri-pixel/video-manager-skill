from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

import anthropic

from .transcriber import Transcript


CLIP_CATEGORIES = [
    "one-liner",
    "funny",
    "motivational",
    "relatable",
    "viral",
    "argument",
    "tip",
    "emotional",
    "surprising",
]

ANALYSIS_PROMPT = """\
You are a viral short-form content expert for Instagram Reels, YouTube Shorts, and TikTok.

Analyze the transcript below and identify the BEST clips to extract.

TRANSCRIPT (with timestamps):
{transcript}

VIDEO DURATION: {duration}s

Find 5-10 clips that match one or more of these categories:
- **one-liner**: A memorable, quotable single statement
- **funny**: Humorous moment that will make viewers laugh or smile
- **motivational**: Inspiring or uplifting moment with a strong message
- **relatable**: Something viewers immediately connect with from daily life
- **viral**: High share potential — surprising, controversial, or mind-blowing
- **argument**: Strong opinion, debate, or counter-intuitive take
- **tip**: Practical advice, hack, or "how-to" moment
- **emotional**: Moving or heartfelt moment
- **surprising**: Unexpected fact, reveal, or twist

Rules for each clip:
1. Duration MUST be between 15–60 seconds
2. Must have a compelling hook in the FIRST 3 seconds
3. Must make sense WITHOUT watching the rest of the video
4. Prefer moments with high energy, clear speech, and emotional impact
5. Avoid clips that are mid-sentence or cut off awkwardly

For "hook_text": write a short, punchy caption (max 10 words) that would appear on screen
to grab attention — e.g., "Nobody tells you this 🤯" or "This changed everything..."

Return ONLY a valid JSON array. No markdown, no explanation, just the array:
[
  {{
    "title": "Short descriptive title (5-8 words)",
    "category": "one-liner|funny|motivational|relatable|viral|argument|tip|emotional|surprising",
    "hook_text": "Catchy on-screen caption (max 10 words)",
    "start_time": 10.5,
    "end_time": 45.2,
    "virality_score": 8,
    "reason": "One sentence: why this will go viral"
  }}
]

Order by virality_score descending. Return ONLY the JSON array.
"""


@dataclass
class ClipSuggestion:
    title: str
    category: str
    hook_text: str
    start_time: float
    end_time: float
    virality_score: int
    reason: str

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


def _parse_clips(response_text: str) -> List[ClipSuggestion]:
    """Parse raw LLM text into ClipSuggestion objects."""
    text = response_text.strip()
    if text.startswith("```"):
        text = "\n".join(
            line for line in text.splitlines()
            if not line.startswith("```")
        ).strip()

    # Find the JSON array even if the model wrapped it in prose
    start_idx = text.find("[")
    end_idx = text.rfind("]") + 1
    if start_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx]

    clips_data: list = json.loads(text)

    clips: List[ClipSuggestion] = []
    for item in clips_data:
        start = float(item["start_time"])
        end = float(item["end_time"])
        duration = end - start

        if duration < 5:
            end = start + 15
        if duration > 90:
            end = start + 60

        clips.append(
            ClipSuggestion(
                title=item["title"],
                category=item.get("category", "viral"),
                hook_text=item.get("hook_text", ""),
                start_time=start,
                end_time=end,
                virality_score=int(item.get("virality_score", 5)),
                reason=item.get("reason", ""),
            )
        )

    clips.sort(key=lambda c: c.virality_score, reverse=True)
    return clips


def analyze_transcript(
    transcript: Transcript,
    api_key: str,
    model: str = "claude-opus-4-5",
    video_duration: int = 0,
) -> List[ClipSuggestion]:
    """Send transcript to Claude API and get back viral clip suggestions."""
    client = anthropic.Anthropic(api_key=api_key)

    lines = [f"[{seg.start:.1f}s – {seg.end:.1f}s] {seg.text}" for seg in transcript.segments]
    prompt = ANALYSIS_PROMPT.format(
        transcript="\n".join(lines),
        duration=video_duration or "unknown",
    )

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    return _parse_clips(message.content[0].text)


def analyze_transcript_local(
    transcript: Transcript,
    ollama_model: str = "llama3.2",
    video_duration: int = 0,
) -> List[ClipSuggestion]:
    """
    Analyze transcript using a local Ollama model — no API key required.

    Requires Ollama to be installed and running: https://ollama.com
    Then pull a model: ollama pull llama3.2

    Recommended models (quality vs size):
      llama3.2       ~2 GB  — good, fast on Apple Silicon
      llama3.1:8b    ~5 GB  — better quality
      mistral        ~4 GB  — good alternative
      qwen2.5:7b     ~4 GB  — strong for structured JSON output
    """
    try:
        import ollama as _ollama
    except ImportError:
        raise ImportError(
            "ollama Python package is not installed.\n"
            "Install with: pip install ollama\n"
            "Also install Ollama itself from: https://ollama.com"
        )

    lines = [f"[{seg.start:.1f}s – {seg.end:.1f}s] {seg.text}" for seg in transcript.segments]
    prompt = ANALYSIS_PROMPT.format(
        transcript="\n".join(lines),
        duration=video_duration or "unknown",
    )

    try:
        response = _ollama.chat(
            model=ollama_model,
            messages=[{"role": "user", "content": prompt}],
        )
        # Handle both dict and object response styles
        if hasattr(response, "message"):
            response_text = response.message.content
        else:
            response_text = response["message"]["content"]
    except Exception as exc:
        if "connection" in str(exc).lower() or "refused" in str(exc).lower():
            raise RuntimeError(
                "Cannot connect to Ollama. Make sure it is running.\n"
                "  macOS/Linux: ollama serve\n"
                "  Or open the Ollama desktop app."
            ) from exc
        raise

    return _parse_clips(response_text)
