# Generate Viral Short Videos

Turn any YouTube video into Instagram Reels / YouTube Shorts / TikTok clips using AI.

## When to use this skill

Invoke this skill when the user:
- Provides a YouTube URL and asks to generate shorts, reels, or clips
- Wants to extract viral moments from a long video
- Asks to create content for social media from a YouTube link

## Prerequisites check

Before running, verify these are set up:

1. **FFmpeg** — check with `ffmpeg -version`. If missing: `brew install ffmpeg`
2. **Python packages** — install with `pip install -r requirements.txt`
3. **API keys** — check that `.env` exists with both keys. If not, run:
   ```bash
   cp .env.example .env
   # Then open .env and fill in both API keys
   ```

## Modes

### API mode (default — best quality)
Requires `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` in `.env`.
```bash
python -m src.main "YOUTUBE_URL"
```

### Local mode (FREE — no API keys)
Uses faster-whisper + Ollama locally on your machine. Zero cost.
```bash
# One-time setup
pip install faster-whisper ollama
brew install ollama       # macOS
ollama pull llama3.2      # ~2 GB download, done once

# Run in local mode
python -m src.main "YOUTUBE_URL" --local
```

## How to run

```bash
# API mode — best quality
python -m src.main "YOUTUBE_URL"

# Local mode — free, no API keys
python -m src.main "YOUTUBE_URL" --local

# Local mode with better models (slower but more accurate)
python -m src.main "YOUTUBE_URL" --local --whisper-model large-v3 --ollama-model llama3.1:8b

# Generate only funny and viral clips (max 3)
python -m src.main "YOUTUBE_URL" --categories "funny,viral" -n 3

# Higher quality filter (min score 8/10)
python -m src.main "YOUTUBE_URL" --min-score 8

# Custom output folder
python -m src.main "YOUTUBE_URL" --output ./my-shorts

# Keep downloaded source files after processing
python -m src.main "YOUTUBE_URL" --no-cleanup
```

## CLI options

| Option | Default | Description |
|--------|---------|-------------|
| `--output / -o` | `./output` | Where to save the MP4 files |
| `--max-clips / -n` | `5` | Max number of clips to generate |
| `--min-score` | `6` | Min virality score (1–10) |
| `--categories / -c` | `all` | Filter: `funny,motivational,relatable,viral,argument,one-liner,tip,emotional,surprising` |
| `--local` | off | Use local free models (faster-whisper + Ollama) |
| `--whisper-model` | `medium` | Local transcription model: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `--ollama-model` | `llama3.2` | Local LLM model (must be pulled with `ollama pull <name>`) |
| `--no-cleanup` | off | Keep temp/source files |

## What happens internally

1. **Download** — yt-dlp downloads the video + audio from YouTube
2. **Transcribe** — OpenAI Whisper API transcribes audio with timestamps
3. **Analyze** — Claude AI reads the transcript and finds the best viral moments
4. **Edit** — FFmpeg:
   - Extracts each clip at the exact timestamps
   - Crops + scales to **1080×1920** (9:16 portrait — perfect ratio for all platforms)
   - Applies Ken Burns subtle zoom effect
   - Burns **animated captions** (TikTok-style, with hook text at top)
   - Adds fade-in/fade-out transitions
   - Normalizes audio levels

## Output

Files are saved as: `01_funny_Clip_Title.mp4`, `02_viral_Another_Moment.mp4`, ...

Each MP4 is:
- **Resolution**: 1080×1920 (9:16)
- **Video**: H.264, 30fps, CRF 20
- **Audio**: AAC 192kbps, normalized
- **Compatibility**: Works on Instagram, YouTube, TikTok, X/Twitter

## Costs (per video processed)

| Service | Cost estimate |
|---------|--------------|
| OpenAI Whisper (30 min audio) | ~$0.05 |
| Claude analysis | ~$0.02–0.05 |
| **Total** | **~$0.07–0.10 per video** |

## Setup (first time only)

```bash
cd /path/to/video-manager-skill
brew install ffmpeg          # macOS only
pip install -r requirements.txt
cp .env.example .env
# Edit .env and paste your API keys
```

## Troubleshooting

- **"No clips matched your filters"** — lower `--min-score` or use `--categories all`
- **FFmpeg error on zoompan** — your FFmpeg might not support all filters; try `brew upgrade ffmpeg`
- **Download fails** — the video might be private, age-restricted, or region-locked
- **Transcription is inaccurate** — check audio quality; background music makes it harder
