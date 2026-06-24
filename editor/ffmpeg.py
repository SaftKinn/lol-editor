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


def _ffprobe(args: list[str]) -> dict:
    """Run ffprobe with JSON output and return the parsed dict."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-of", "json", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(out.stdout)


def probe_duration(path: Path) -> float:
    """Return the duration of a media file in seconds (via ffprobe)."""
    data = _ffprobe(["-show_entries", "format=duration", str(path)])
    return float(data["format"]["duration"])


def probe_video(path: Path) -> dict:
    """Return the first video stream's {width, height, fps} (fps as a float)."""
    data = _ffprobe([
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        str(path),
    ])
    s = data["streams"][0]
    num, den = (s["r_frame_rate"].split("/") + ["1"])[:2]
    fps = float(num) / float(den) if float(den) else float(num)
    return {"width": int(s["width"]), "height": int(s["height"]), "fps": fps}


def has_audio(path: Path) -> bool:
    """True if the file has at least one audio stream (intros are often silent)."""
    data = _ffprobe(["-select_streams", "a", "-show_entries", "stream=index", str(path)])
    return bool(data.get("streams"))
