"""Clip pre-processing: parse filename instructions and apply FFmpeg trims.

The owner embeds processing hints directly in the clip filename:

    "darius bis sekunde 26 gehört zu 1.mp4"
        -> trim to second 26, belongs to game-group 1

    "guter clip schneide die ersten 1.75 sekunden weg gehört mit 1 zusammen.mp4"
        -> cut first 1.75 s, game-group 1

    "guter clip aber ohne ton ist mit stimmen.mp4"
        -> mute game audio (voices on stream 0), only music plays

    "guter clip aber entferne den clipton.mp4"
        -> same as "ohne ton"

    "gut bis sekunde 33 gehört zu 1.mp4"
        -> trim to s33, game-group 1

Trimmed copies are written to output/_prep/ so the originals stay untouched.
The `group` field is returned for future montage grouping but not yet acted on
automatically (manual montage via editor.montage covers it for now).
"""

import re
from pathlib import Path

from editor.ffmpeg import run


def parse_filename(stem: str) -> dict:
    """Extract processing hints from a clip stem (filename without extension).

    Returns a dict with keys:
        trim_start  float | None   — cut this many seconds from the beginning
        trim_end    float | None   — cut video at this second
        mute_game   bool           — remove game audio (keep only music)
        group       int | None     — game-group number for montage ordering
    """
    info: dict = {"trim_start": None, "trim_end": None, "mute_game": False, "group": None}

    # "bis sekunde 26" / "bis sekunde 33.5"
    m = re.search(r"bis sekunde (\d+(?:[.,]\d+)?)", stem, re.IGNORECASE)
    if m:
        info["trim_end"] = float(m.group(1).replace(",", "."))

    # "schneide die ersten 1.75 sekunden weg"
    m = re.search(r"schneide die ersten (\d+(?:[.,]\d+)?)\s*sekunden?\s*weg", stem, re.IGNORECASE)
    if m:
        info["trim_start"] = float(m.group(1).replace(",", "."))

    # "ohne ton" or "entferne den clipton"
    if re.search(r"ohne ton|entferne den clipton", stem, re.IGNORECASE):
        info["mute_game"] = True

    # "gehört zu 1" / "gehört mit 1" / "selbes spiel wie 1"
    m = re.search(r"geh[öo]rt (?:zu|mit) (\d+)", stem, re.IGNORECASE)
    if not m:
        m = re.search(r"selbes spiel wie (\d+)", stem, re.IGNORECASE)
    if m:
        info["group"] = int(m.group(1))

    return info


def preprocess(clip: Path, scratch_dir: Path) -> tuple[Path, dict]:
    """Apply trim instructions embedded in the clip filename.

    If no trim is needed the original path is returned unchanged (fast path).
    Trimmed copies go to scratch_dir/_prep_<original_name>.mp4 and are reused
    on re-runs so the pipeline stays idempotent.

    Returns (clip_to_use, meta_dict).
    """
    meta = parse_filename(clip.stem)

    if meta["trim_start"] is None and meta["trim_end"] is None:
        return clip, meta

    scratch_dir.mkdir(parents=True, exist_ok=True)
    out = scratch_dir / f"_prep_{clip.name}"

    if not out.exists():
        args = ["-i", str(clip)]
        if meta["trim_start"]:
            args += ["-ss", str(meta["trim_start"])]
        if meta["trim_end"]:
            dur = meta["trim_end"] - (meta["trim_start"] or 0.0)
            args += ["-t", f"{dur:.3f}"]
        args += ["-c", "copy", str(out)]
        print(f"  prep: trim {clip.name}"
              + (f"  start={meta['trim_start']}s" if meta["trim_start"] else "")
              + (f"  end={meta['trim_end']}s" if meta["trim_end"] else ""))
        run(args)
    else:
        print(f"  prep: reusing trimmed {out.name}")

    return out, meta
