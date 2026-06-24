"""Stage: highlights.py — cut highlight windows from a _moments.json sidecar.

Reads the sidecar written by detect.py and cuts one short MP4 per detected moment.
These clips drop straight into the existing pipeline (hand one to edit.py, or batch
a folder with pipeline.py).

No re-encode: video is copied stream-for-stream (-c copy) so cuts are fast and
lossless. Start is keyframe-aligned (may be a few frames early — fine for raw clips
that go through edit.py next anyway).

Usage:
    python -m editor.highlights output/my_game_moments.json   # direct sidecar path
    python -m editor.highlights input/my_game.mp4             # finds sidecar for you
    python -m editor.highlights my_game.mp4                   # bare name from input/

Output:
    output/<stem>_highlights/
        00_pentakill.mp4
        01_ace.mp4
        …
"""

import json
import sys
from pathlib import Path

from editor.config import ROOT, load_config
from editor.ffmpeg import run as ff_run


def _resolve_sidecar(given: str, input_dir: Path, output_dir: Path) -> Path:
    """Return the _moments.json path for a sidecar, video path, or bare clip name."""
    p = Path(given)

    # Already a JSON sidecar (real path or bare name in output/)
    if p.suffix == ".json":
        if p.exists():
            return p
        alt = output_dir / given
        if alt.exists():
            return alt
        raise SystemExit(f"Sidecar not found: {given}")

    # Video path or bare name — find the matching sidecar in output/
    if not p.exists():
        alt = input_dir / given
        if alt.exists():
            p = alt
        else:
            # Search preset sub-folders too
            hits = list(input_dir.rglob(given))
            if hits:
                p = hits[0]
            else:
                raise SystemExit(f"File not found: {given} (looked in {input_dir} too)")

    sidecar = output_dir / f"{p.stem}_moments.json"
    if not sidecar.exists():
        raise SystemExit(
            f"No sidecar found for {p.name}.\n"
            f"Expected: {sidecar}\n"
            f"Run detect.py first:  python -m editor.detect {p}"
        )
    return sidecar


def _find_source(clip_name: str, input_dir: Path) -> Path:
    """Locate the original clip under input/ (including preset sub-folders)."""
    # Exact path first
    direct = Path(clip_name)
    if direct.exists():
        return direct

    # Search anywhere under input/
    for hit in input_dir.rglob(clip_name):
        return hit

    raise SystemExit(
        f"Source clip '{clip_name}' not found under {input_dir}.\n"
        "Move the original clip into input/ (or a preset sub-folder) first."
    )


def cut_highlights(video: Path, moments: list[dict], out_dir: Path) -> list[Path]:
    """Cut one MP4 per moment into out_dir. Returns list of written paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for i, m in enumerate(moments):
        label    = m["label"]
        start    = float(m["window_start"])
        end      = float(m["window_end"])
        duration = round(end - start, 3)

        out_path = out_dir / f"{i:02d}_{label}.mp4"
        print(f"  [{i:02d}] {label:<14}  {start:.1f}s – {end:.1f}s  ({duration:.1f}s)")

        ff_run([
            "-ss", str(start),
            "-i",  str(video),
            "-t",  str(duration),
            "-c",  "copy",
            "-movflags", "+faststart",
            str(out_path),
        ])
        written.append(out_path)

    return written


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print("Usage: python -m editor.highlights <clip_or_sidecar>", file=sys.stderr)
        return 1

    config     = load_config()
    input_dir  = ROOT / config["paths"]["input_dir"]
    output_dir = ROOT / config["paths"]["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    sidecar = _resolve_sidecar(argv[0], input_dir, output_dir)
    data    = json.loads(sidecar.read_text(encoding="utf-8"))

    moments = data.get("moments", [])
    if not moments:
        print(f"No moments in {sidecar.name} — nothing to cut.")
        return 0

    video   = _find_source(data["clip"], input_dir)
    stem    = Path(data["clip"]).stem
    out_dir = output_dir / f"{stem}_highlights"

    print(f"Source:  {video}")
    print(f"Sidecar: {sidecar.name}  ({len(moments)} moment(s))")
    print(f"Output:  {out_dir}\n")

    written = cut_highlights(video, moments, out_dir)

    print(f"\nDone — {len(written)} clip(s) written.")
    print(f"Next steps:")
    print(f"  Single clip:  python -m editor.edit {out_dir / '00_*.mp4'}")
    print(f"  Whole batch:  python -m editor.pipeline {out_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
