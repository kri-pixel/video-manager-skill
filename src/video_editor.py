from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from .analyzer import ClipSuggestion
from .transcriber import Transcript, TranscriptSegment


# ─── helpers ──────────────────────────────────────────────────────────────────

def _require_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise EnvironmentError(
            "FFmpeg not found. Install with: brew install ffmpeg"
        )


def _probe_dimensions(video_path: Path) -> Tuple[int, int]:
    """Return (width, height) of the first video stream."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            return int(stream["width"]), int(stream["height"])
    raise ValueError(f"No video stream found in {video_path}")


def _crop_params_for_9_16(orig_w: int, orig_h: int) -> Tuple[int, int, int, int]:
    """Return (crop_w, crop_h, crop_x, crop_y) to make a 9:16 crop."""
    target_ar = 9 / 16
    if (orig_w / orig_h) > target_ar:
        # Landscape source → crop horizontally
        crop_h = orig_h
        crop_w = int(orig_h * target_ar)
        crop_x = (orig_w - crop_w) // 2
        crop_y = 0
    else:
        # Portrait / square source → crop vertically
        crop_w = orig_w
        crop_h = int(orig_w / target_ar)
        crop_x = 0
        crop_y = (orig_h - crop_h) // 2
    return crop_w, crop_h, crop_x, crop_y


# ─── ASS subtitle generation ──────────────────────────────────────────────────

def _secs_to_ass(t: float) -> str:
    """Convert seconds → ASS time H:MM:SS.cc"""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    cs = int((s % 1) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,68,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,1,0,1,4,2,2,60,60,200,1
Style: Hook,Arial,52,&H0000FFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,3,2,8,60,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# Category → color code for hook text (ASS BGR hex)
_CATEGORY_COLOR: dict[str, str] = {
    "funny":        "&H0000D7FF",  # yellow
    "motivational": "&H0000FF7F",  # green
    "viral":        "&H000000FF",  # red
    "argument":     "&H00FF6347",  # orange
    "one-liner":    "&H00FFFFFF",  # white
    "relatable":    "&H00FFB6C1",  # pink
    "tip":          "&H0000FFFF",  # cyan
    "emotional":    "&H00DDA0DD",  # purple
    "surprising":   "&H00FFD700",  # gold
}


def _build_ass(
    segments: List[TranscriptSegment],
    hook_text: str,
    category: str,
    clip_start: float,
    clip_end: float,
) -> str:
    clip_len = clip_end - clip_start
    lines: List[str] = []

    # Hook overlay — top of screen for first 3 seconds
    hook_color = _CATEGORY_COLOR.get(category, "&H00FFFFFF")
    clean_hook = re.sub(r'[{}\\]', '', hook_text)
    hook_line = (
        f"Dialogue: 0,{_secs_to_ass(0)},{_secs_to_ass(min(3.5, clip_len))},"
        f"Hook,,0,0,0,,{{\\c{hook_color}\\fad(300,300)}}{clean_hook}"
    )
    lines.append(hook_line)

    # Caption subtitles — bottom of screen
    for seg in segments:
        rel_start = seg.start - clip_start
        rel_end = seg.end - clip_start

        if rel_end <= 0 or rel_start >= clip_len:
            continue

        rel_start = max(0.0, rel_start)
        rel_end = min(clip_len, rel_end)

        # Escape ASS special characters
        text = re.sub(r'[{}\\]', '', seg.text.strip())
        # Break long lines at word boundaries
        if len(text) > 42:
            words = text.split()
            mid = len(words) // 2
            text = " ".join(words[:mid]) + "\\N" + " ".join(words[mid:])

        dialogue = (
            f"Dialogue: 0,{_secs_to_ass(rel_start)},{_secs_to_ass(rel_end)},"
            f"Default,,0,0,0,,{{\\fad(150,150)}}{text}"
        )
        lines.append(dialogue)

    return ASS_HEADER + "\n".join(lines)


# ─── main edit function ───────────────────────────────────────────────────────

@dataclass
class GeneratedClip:
    path: Path
    title: str
    category: str
    hook_text: str
    virality_score: int
    duration: float


def create_short_video(
    video_path: Path,
    clip: ClipSuggestion,
    transcript: Transcript,
    output_path: Path,
    target_width: int = 1080,
    target_height: int = 1920,
) -> GeneratedClip:
    """
    Extract a clip, crop/scale to 9:16, burn animated captions, export MP4.

    Output is ready for Instagram Reels / YouTube Shorts / TikTok.
    """
    _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    orig_w, orig_h = _probe_dimensions(video_path)
    crop_w, crop_h, crop_x, crop_y = _crop_params_for_9_16(orig_w, orig_h)

    clip_duration = clip.end_time - clip.start_time

    # Filter transcript to just the clip's segments
    clip_segments = [
        seg for seg in transcript.segments
        if seg.end > clip.start_time and seg.start < clip.end_time
    ]

    # Write ASS subtitle file to a temp path (no spaces to avoid FFmpeg quoting issues)
    tmp_dir = Path(tempfile.gettempdir())
    ass_path = tmp_dir / f"shorts_captions_{os.getpid()}.ass"
    ass_path.write_text(
        _build_ass(clip_segments, clip.hook_text, clip.category, clip.start_time, clip.end_time),
        encoding="utf-8",
    )

    # Escape the ASS path for FFmpeg filter (colons are special on Windows; on macOS fine)
    ass_filter = f"ass={ass_path}"

    # Ken Burns zoom-in effect: scale from 100% → 105% over the clip duration
    zoom_expr = f"1.0+0.05*on/({clip_duration}*30)"   # 30 fps assumption

    vf = ",".join([
        # Crop to 9:16
        f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}",
        # Scale to target resolution
        f"scale={target_width}:{target_height}:flags=lanczos",
        # Subtle Ken Burns zoom
        f"zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={target_width}x{target_height}:fps=30",
        # Fade in / fade out
        f"fade=t=in:st=0:d=0.4",
        f"fade=t=out:st={max(0, clip_duration - 0.4):.3f}:d=0.4",
        # Burn subtitles
        ass_filter,
    ])

    af = ",".join([
        f"afade=t=in:ss=0:d=0.3",
        f"afade=t=out:st={max(0, clip_duration - 0.3):.3f}:d=0.3",
        "loudnorm",   # normalize audio levels (important for mobile)
    ])

    cmd = [
        "ffmpeg",
        "-y",                          # overwrite output
        "-ss", str(clip.start_time),   # fast seek (input side)
        "-t", str(clip_duration),      # duration
        "-i", str(video_path),
        "-vf", vf,
        "-af", af,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-pix_fmt", "yuv420p",          # broad compatibility
        "-movflags", "+faststart",      # web/mobile streaming optimization
        "-r", "30",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    ass_path.unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed for clip '{clip.title}':\n{result.stderr[-2000:]}"
        )

    return GeneratedClip(
        path=output_path,
        title=clip.title,
        category=clip.category,
        hook_text=clip.hook_text,
        virality_score=clip.virality_score,
        duration=clip_duration,
    )
