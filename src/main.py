#!/usr/bin/env python3
"""Short Video Generator — turn any YouTube video into viral Reels/Shorts."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

load_dotenv()

console = Console()


# ─── helpers ──────────────────────────────────────────────────────────────────

def _check_env(key: str) -> str:
    val = os.getenv(key, "")
    if not val:
        console.print(f"[red]Error:[/red] {key} is not set. Add it to your .env file.")
        sys.exit(1)
    return val


def _check_ollama(model: str) -> None:
    """Verify Ollama is running and the requested model is available."""
    import subprocess
    if not shutil.which("ollama"):
        console.print(
            "[red]Error:[/red] Ollama not found.\n"
            "  Install from: https://ollama.com\n"
            "  Then pull a model: [bold]ollama pull llama3.2[/bold]"
        )
        sys.exit(1)
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if model not in result.stdout:
        console.print(
            f"[yellow]Model '{model}' not found locally. Pulling it now...[/yellow]"
        )
        subprocess.run(["ollama", "pull", model], check=True)


def _check_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        console.print(
            "[red]Error:[/red] FFmpeg not found.\n"
            "  macOS:  brew install ffmpeg\n"
            "  Ubuntu: sudo apt install ffmpeg"
        )
        sys.exit(1)


def _safe_filename(s: str) -> str:
    import re
    return re.sub(r"[^\w\-]", "_", s)[:45]


# ─── CLI ──────────────────────────────────────────────────────────────────────

@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("url")
@click.option(
    "--output", "-o",
    default="./output",
    show_default=True,
    help="Directory where generated MP4 shorts are saved.",
)
@click.option(
    "--max-clips", "-n",
    default=5,
    show_default=True,
    help="Maximum number of short clips to generate.",
)
@click.option(
    "--min-score",
    default=6,
    show_default=True,
    help="Minimum virality score (1–10) to include a clip.",
)
@click.option(
    "--categories", "-c",
    default="all",
    show_default=True,
    help=(
        "Comma-separated list of categories to include. "
        "Options: funny, motivational, relatable, viral, argument, one-liner, tip, emotional, surprising"
    ),
)
@click.option(
    "--local",
    is_flag=True,
    default=False,
    help="Use local models only — no API keys required. Uses faster-whisper + Ollama.",
)
@click.option(
    "--whisper-model",
    default="medium",
    show_default=True,
    help="[--local] faster-whisper model size: tiny, base, small, medium, large-v3.",
)
@click.option(
    "--ollama-model",
    default="llama3.2",
    show_default=True,
    help="[--local] Ollama model name. Run 'ollama list' to see installed models.",
)
@click.option(
    "--no-cleanup",
    is_flag=True,
    default=False,
    help="Keep downloaded source files in ./temp after processing.",
)
def main(
    url: str,
    output: str,
    max_clips: int,
    min_score: int,
    categories: str,
    local: bool,
    whisper_model: str,
    ollama_model: str,
    no_cleanup: bool,
) -> None:
    """Generate viral short-form videos from a YouTube URL.

    \b
    MODES
      API mode (default, best quality):
        python -m src.main "URL"
        Requires ANTHROPIC_API_KEY + OPENAI_API_KEY in .env

      Local mode (free, no API keys):
        python -m src.main "URL" --local
        Requires: pip install faster-whisper ollama
                  brew install ollama && ollama pull llama3.2

    \b
    EXAMPLES
      python -m src.main "https://youtube.com/watch?v=VIDEO_ID"
      python -m src.main "https://youtu.be/VIDEO_ID" --local
      python -m src.main "https://youtu.be/VIDEO_ID" --local --whisper-model small --ollama-model mistral
      python -m src.main "https://youtu.be/VIDEO_ID" -n 3 --categories "funny,viral"
    """
    from .downloader import download_video
    from .transcriber import transcribe_audio, transcribe_audio_local
    from .analyzer import analyze_transcript, analyze_transcript_local
    from .video_editor import create_short_video

    _check_ffmpeg()

    # Validate prerequisites depending on mode
    anthropic_key = openai_key = ""
    if local:
        _check_ollama(ollama_model)
    else:
        anthropic_key = _check_env("ANTHROPIC_API_KEY")
        openai_key = _check_env("OPENAI_API_KEY")

    output_dir = Path(output)
    temp_dir = Path("./temp")
    mode_label = "[yellow]LOCAL — free, no API keys[/yellow]" if local else "[cyan]API — OpenAI Whisper + Claude[/cyan]"

    console.print(
        Panel.fit(
            f"[bold cyan]Short Video Generator[/bold cyan]\n"
            f"YouTube → Instagram Reels / YouTube Shorts / TikTok\n"
            f"Mode: {mode_label}",
            border_style="cyan",
        )
    )
    console.print(f"\n[dim]Input:[/dim]  [cyan]{url}[/cyan]")
    console.print(f"[dim]Output:[/dim] [cyan]{output_dir}[/cyan]\n")

    # ── Step 1: Download ───────────────────────────────────────────────────────
    with console.status("[bold green]Step 1/4 — Downloading video...[/bold green]"):
        video_info = download_video(url, temp_dir)

    console.print(
        f"[green]✓[/green] Downloaded: [bold]{video_info.title}[/bold]  "
        f"[dim]({video_info.duration}s • {video_info.channel})[/dim]"
    )

    # ── Step 2: Transcribe ─────────────────────────────────────────────────────
    if local:
        transcribe_label = f"Step 2/4 — Transcribing locally with faster-whisper [{whisper_model}]..."
        with console.status(f"[bold green]{transcribe_label}[/bold green]"):
            transcript = transcribe_audio_local(video_info.audio_path, model_size=whisper_model)
    else:
        with console.status("[bold green]Step 2/4 — Transcribing audio with OpenAI Whisper...[/bold green]"):
            transcript = transcribe_audio(video_info.audio_path, openai_key)

    console.print(
        f"[green]✓[/green] Transcribed: {len(transcript.segments)} segments  "
        f"[dim](lang: {transcript.language})[/dim]"
    )

    # ── Step 3: Analyze ────────────────────────────────────────────────────────
    if local:
        analyze_label = f"Step 3/4 — Analyzing with Ollama [{ollama_model}]..."
        with console.status(f"[bold green]{analyze_label}[/bold green]"):
            all_clips = analyze_transcript_local(
                transcript,
                ollama_model=ollama_model,
                video_duration=video_info.duration,
            )
    else:
        with console.status("[bold green]Step 3/4 — Analyzing with Claude AI...[/bold green]"):
            all_clips = analyze_transcript(
                transcript,
                anthropic_key,
                video_duration=video_info.duration,
            )

    # Apply filters
    filtered = all_clips
    if categories.lower() != "all":
        allowed = {c.strip().lower() for c in categories.split(",")}
        filtered = [c for c in filtered if c.category.lower() in allowed]

    filtered = [c for c in filtered if c.virality_score >= min_score]
    filtered = filtered[:max_clips]

    if not filtered:
        console.print(
            "[yellow]Warning:[/yellow] No clips matched your filters. "
            "Try lowering --min-score or expanding --categories."
        )
        sys.exit(0)

    # Display clip candidates table
    table = Table(title=f"Viral Clip Candidates ({len(filtered)} selected)", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold", min_width=25)
    table.add_column("Category", style="cyan", width=12)
    table.add_column("Time", style="yellow", width=14)
    table.add_column("Dur", style="dim", width=5)
    table.add_column("Score", style="green", width=8)
    table.add_column("Hook", style="italic", min_width=22)

    for i, clip in enumerate(filtered, 1):
        stars = "★" * clip.virality_score + "☆" * (10 - clip.virality_score)
        table.add_row(
            str(i),
            clip.title[:35],
            clip.category,
            f"{clip.start_time:.0f}s → {clip.end_time:.0f}s",
            f"{clip.duration:.0f}s",
            f"{clip.virality_score}/10",
            clip.hook_text[:30],
        )

    console.print(table)

    # ── Step 4: Generate videos ────────────────────────────────────────────────
    console.print(f"\n[bold green]Step 4/4 — Generating {len(filtered)} short videos...[/bold green]")

    generated = []
    failed = []

    for i, clip in enumerate(filtered, 1):
        safe = _safe_filename(clip.title)
        filename = f"{i:02d}_{clip.category}_{safe}.mp4"
        out_path = output_dir / filename

        with console.status(
            f"[bold green]  [{i}/{len(filtered)}] {clip.title[:50]}...[/bold green]"
        ):
            try:
                result = create_short_video(
                    video_path=video_info.video_path,
                    clip=clip,
                    transcript=transcript,
                    output_path=out_path,
                )
                generated.append(result)
                size_mb = out_path.stat().st_size / (1024 * 1024)
                console.print(
                    f"  [green]✓[/green] [bold]{filename}[/bold]  "
                    f"[dim]{result.duration:.0f}s • {size_mb:.1f} MB[/dim]"
                )
            except Exception as exc:
                failed.append((clip.title, str(exc)))
                console.print(f"  [red]✗[/red] Failed: {clip.title[:40]} — {exc}")

    # Cleanup temp files unless --no-cleanup
    if not no_cleanup and temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

    # ── Summary ────────────────────────────────────────────────────────────────
    console.rule("[bold green]Done[/bold green]")
    console.print(f"\n[bold]{len(generated)}[/bold] shorts saved to [cyan]{output_dir.resolve()}[/cyan]")

    if failed:
        console.print(f"[yellow]{len(failed)} clips failed to generate.[/yellow]")

    console.print(
        "\n[dim]Ready to upload to:[/dim]\n"
        "  • Instagram Reels  (1080×1920, up to 90s)\n"
        "  • YouTube Shorts   (1080×1920, up to 60s)\n"
        "  • TikTok           (1080×1920, up to 60s)"
    )


if __name__ == "__main__":
    main()
