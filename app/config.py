"""Runtime configuration loaded from the project .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")


def root_dir() -> Path:
    """Project root, the folder that contains .env and data/."""
    return _ROOT


def get_env(name: str) -> str:
    """Return a required environment variable, or raise with its name."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Set {name} in the project .env file.")
    return value
