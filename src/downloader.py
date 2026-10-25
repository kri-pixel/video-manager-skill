from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yt_dlp


@dataclass
class VideoInfo:
    title: str
    duration: int  # seconds
    video_path: Path
    audio_path: Path
    thumbnail_url: str
    channel: str


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[^\w\s-]', '', name).strip()[:60]


def download_video(url: str, output_dir: Path) -> VideoInfo:
    """Download a YouTube video and extract a separate MP3 for transcription."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Probe metadata first (no download)
    ydl_opts_info: dict = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        info = ydl.extract_info(url, download=False)

    title: str = info.get("title", "video")
    duration: int = int(info.get("duration", 0))
    thumbnail_url: str = info.get("thumbnail", "")
    channel: str = info.get("uploader", "")

    safe_title = _sanitize_filename(title)
    video_path = output_dir / "source_video.mp4"
    audio_path = output_dir / "source_audio.mp3"

    # Download best video + audio merged into MP4
    ydl_opts_video: dict = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(video_path.with_suffix("")),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
        ydl.download([url])

    # Download audio-only MP3 for Whisper transcription
    ydl_opts_audio: dict = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": str(audio_path.with_suffix("")),
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
        ydl.download([url])

    # yt-dlp adds the extension itself
    actual_video = output_dir / "source_video.mp4"
    actual_audio = output_dir / "source_audio.mp3"

    return VideoInfo(
        title=title,
        duration=duration,
        video_path=actual_video,
        audio_path=actual_audio,
        thumbnail_url=thumbnail_url,
        channel=channel,
    )
