"""Load LoL Editor settings from config/config.toml (or the example as a fallback)."""

import tomllib
from pathlib import Path

# Project root = the folder above editor/. Every path is built from here so the
# tool works no matter which directory you run it from.
ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    """Read settings from config/config.toml, falling back to the example."""
    for name in ("config/config.toml", "config/config.example.toml"):
        path = ROOT / name
        if path.exists():
            with path.open("rb") as f:
                return tomllib.load(f)
    raise FileNotFoundError("No config file found in config/.")
