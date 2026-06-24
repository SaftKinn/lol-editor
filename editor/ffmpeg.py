"""Tiny wrappers around the ffmpeg / ffprobe command-line tools.

Keeping every ffmpeg call behind these helpers means the rest of the code reads like
plain steps, and there is one place to look when something about the encoding changes.
"""

import json
import subprocess
from pathlib import Path


def run(args: list[str]) -> None:
    """Run an ffmpeg command. Raises if ffmpeg exits non-zero.

    `args` is everything AFTER the word `ffmpeg`. We always pass -y (overwrite output)
    and -hide_banner so the logs stay readable.
    """
    cmd = ["ffmpeg", "-hide_banner", "-y", *args]
    subprocess.run(cmd, check=True)


def probe_duration(path: Path) -> float:
    """Return the duration of a media file in seconds (via ffprobe)."""
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])
