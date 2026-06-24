"""Phase 2: presets + music pools.

A *preset* is just an input sub-folder paired with a matching music pool: drop a clip
in input/hype/ and it gets scored from music/hype/, with zero per-clip choices. This
keeps the editing style + music following the clip automatically (ADR 0004, ADR 0006).

Track selection within a pool is DETERMINISTIC per clip: the same clip always maps to
the same track, so re-runs stay reproducible (ADR 0007), while different clips spread
across the pool. We hash the clip name with md5 rather than Python's built-in hash(),
because the built-in is salted per process and would not be stable across runs.
"""

import hashlib
from pathlib import Path

from editor.config import ROOT

# Audio file types accepted as music tracks.
MUSIC_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}


def detect_preset(video: Path, config: dict) -> str | None:
    """Return the preset for a clip, taken from its parent folder name.

    input/hype/clip.mp4 -> "hype"   (when "hype" is a configured preset)
    input/clip.mp4      -> None      (no preset sub-folder; uses the music/ root)
    """
    names = config.get("presets", {}).get("names", [])
    parent = video.parent.name
    return parent if parent in names else None


def _tracks_in(folder: Path) -> list[Path]:
    """Audio files directly inside a folder, sorted for a stable, repeatable order."""
    if not folder.is_dir():
        return []
    tracks = [
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in MUSIC_EXTENSIONS
    ]
    return sorted(tracks)


def _pick(tracks: list[Path], key: str) -> Path:
    """Map a key (the clip name) to one track via a stable hash. Pure + testable."""
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return tracks[int(digest, 16) % len(tracks)]


def choose_music(video: Path, config: dict) -> Path:
    """Pick a music track for a clip based on its preset.

    - Preset folder (input/hype/) -> pick from the matching pool (music/hype/).
    - No preset (clip directly in input/) -> pick from the top-level music/ folder.
    - Empty preset pool -> fall back to the top-level music/ folder, so a missing
      pool degrades gracefully instead of failing the whole batch.

    Raises SystemExit with a clear message if no track can be found at all.
    """
    music_root = ROOT / config["paths"]["music_dir"]
    preset = detect_preset(video, config)

    pool = music_root / preset if preset else music_root
    tracks = _tracks_in(pool)

    if not tracks and preset:
        # Preset pool is empty — fall back to whatever sits in music/ root.
        pool = music_root
        tracks = _tracks_in(music_root)

    if not tracks:
        raise SystemExit(
            f"No music tracks found in {pool}. Add royalty-free tracks "
            f"({', '.join(sorted(MUSIC_EXTENSIONS))}) — see ADR 0004."
        )

    return _pick(tracks, video.stem)
