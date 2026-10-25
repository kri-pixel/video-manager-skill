import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    output_dir: Path = field(default_factory=lambda: Path("./output"))
    temp_dir: Path = field(default_factory=lambda: Path("./temp"))
    target_width: int = 1080
    target_height: int = 1920
    max_clip_duration: int = 60   # seconds
    min_clip_duration: int = 10   # seconds
    max_clips: int = 10
    claude_model: str = "claude-opus-4-5"


config = Config()
