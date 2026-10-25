#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "Setting up Short Video Generator..."

# Check FFmpeg
if ! command -v ffmpeg &>/dev/null; then
  echo "FFmpeg not found. Installing..."
  brew install ffmpeg
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment at .venv ..."
  python3 -m venv "$VENV_DIR"
fi

# Activate and install
source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt

# Ask about local mode
echo ""
read -p "Install local mode packages (faster-whisper + ollama)? Free, no API keys. [y/N] " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
  pip install faster-whisper ollama
  echo "Local packages installed."
fi

# Create .env if missing
if [ ! -f "$PROJECT_DIR/.env" ]; then
  cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
  echo ""
  echo "Created .env — open it and add your API keys (only needed for API mode)."
fi

echo ""
echo "Setup complete!"
echo ""
echo "To activate the environment in a new terminal:"
echo "  source .venv/bin/activate"
echo ""
echo "Then run:"
echo "  python -m src.main \"YOUTUBE_URL\"          # API mode"
echo "  python -m src.main \"YOUTUBE_URL\" --local  # Local mode (free)"
