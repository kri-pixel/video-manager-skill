# Short Video Generator

AI-powered tool that analyzes any YouTube video and automatically generates viral short-form clips — perfectly formatted for **Instagram Reels**, **YouTube Shorts**, and **TikTok**.

## How it works

```
YouTube URL
    ↓
[1] Download video + audio  (yt-dlp)
    ↓
[2] Transcribe with timestamps  (OpenAI Whisper API  OR  faster-whisper locally)
    ↓
[3] AI finds viral moments  (Claude API  OR  Ollama locally)
    ↓
[4] FFmpeg edits each clip:
     • Crop & scale to 1080×1920 (9:16)
     • Ken Burns zoom effect
     • Animated TikTok-style captions
     • Fade in/out transitions
     • Audio normalization
    ↓
Output: ready-to-upload MP4 files
```

## Modes

| | API mode | Local mode |
|---|---|---|
| **Cost** | ~$0.07–0.10/video | Free forever |
| **Quality** | Best | Good |
| **Speed** | Fast | Slower (CPU) |
| **Requirements** | Anthropic + OpenAI API keys | Ollama installed |
| **Flag** | _(default)_ | `--local` |

## What the AI analyzes for

| Category | Description |
|----------|-------------|
| `one-liner` | Memorable, quotable statements |
| `funny` | Humorous moments that make viewers laugh |
| `motivational` | Inspiring or uplifting moments |
| `relatable` | Daily-life moments viewers immediately connect with |
| `viral` | Surprising, shocking, or controversial content |
| `argument` | Strong opinions or counter-intuitive takes |
| `tip` | Practical advice or life hacks |
| `emotional` | Moving or heartfelt moments |
| `surprising` | Unexpected facts, reveals, or twists |

## Prerequisites

- **Python 3.11+**
- **FFmpeg**: `brew install ffmpeg` (macOS) or `sudo apt install ffmpeg` (Ubuntu/Debian)

## Setup

### API mode (best quality)

```bash
# 1. Install FFmpeg
brew install ffmpeg

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure API keys
cp .env.example .env
# Open .env and add your ANTHROPIC_API_KEY and OPENAI_API_KEY
```

### Local mode (free, no API keys)

```bash
# 1. Install FFmpeg
brew install ffmpeg

# 2. Install Python dependencies + local model packages
pip install -r requirements.txt faster-whisper ollama

# 3. Install Ollama and pull a model
brew install ollama       # or download from https://ollama.com
ollama pull llama3.2      # ~2 GB, downloaded once
```

No `.env` file needed in local mode.

## Usage

```bash
# API mode — best quality
python -m src.main "https://youtube.com/watch?v=VIDEO_ID"

# Local mode — free, no API keys
python -m src.main "https://youtube.com/watch?v=VIDEO_ID" --local

# Local mode with larger/better models
python -m src.main "https://youtu.be/VIDEO_ID" --local --whisper-model large-v3 --ollama-model llama3.1:8b

# Generate only funny and viral clips (max 3)
python -m src.main "https://youtu.be/VIDEO_ID" --categories "funny,viral" -n 3

# High-quality filter — only clips scoring 8+/10
python -m src.main "https://youtube.com/watch?v=VIDEO_ID" --min-score 8

# Custom output folder
python -m src.main "https://youtube.com/watch?v=VIDEO_ID" -o ~/Desktop/my-reels
```

### All options

```
Usage: python -m src.main [OPTIONS] URL

Options:
  --output / -o TEXT       Output directory  [default: ./output]
  --max-clips / -n INT     Max clips to generate  [default: 5]
  --min-score INT          Min virality score 1–10  [default: 6]
  --categories / -c TEXT   Filter by category (comma-separated)
  --local                  Use local models — no API keys required
  --whisper-model TEXT     Local transcription model  [default: medium]
  --ollama-model TEXT      Local LLM model  [default: llama3.2]
  --no-cleanup             Keep downloaded source files in ./temp
  -h, --help               Show this message and exit
```

### Local model options

**Transcription** (`--whisper-model`):

| Model | RAM needed | Quality |
|-------|-----------|---------|
| `tiny` / `base` | ~1 GB | passable |
| `small` | ~2 GB | good |
| `medium` | ~5 GB | very good _(default)_ |
| `large-v3` | ~10 GB | best |

**Analysis** (`--ollama-model`):

| Model | Size | Notes |
|-------|------|-------|
| `llama3.2` | ~2 GB | default, fast on Apple Silicon |
| `llama3.1:8b` | ~5 GB | better quality |
| `mistral` | ~4 GB | good alternative |
| `qwen2.5:7b` | ~4 GB | strong structured output |

## Output

Generated files look like:
```
output/
├── 01_viral_Nobody_Tells_You_This.mp4          (25s)
├── 02_funny_When_You_Realize_It.mp4            (18s)
├── 03_motivational_This_Changed_Everything.mp4 (42s)
└── ...
```

Each file is:
- **1080×1920** — the exact 9:16 ratio for Reels/Shorts/TikTok
- H.264 video + AAC audio
- Animated captions + hook text overlay
- Fade transitions + subtle zoom

## Using as a Claude Code skill

This project includes a Claude Code skill. Once you're in this directory, invoke:

```
/generate-shorts
```

Claude will guide you through the process interactively.

## Cost

| Mode | Service | ~Cost per 30-min video |
|------|---------|------------------------|
| API | OpenAI Whisper | $0.05 |
| API | Claude claude-opus-4-5 | $0.02–0.05 |
| API | **Total** | **~$0.07–0.10** |
| Local | faster-whisper + Ollama | **$0.00** |
