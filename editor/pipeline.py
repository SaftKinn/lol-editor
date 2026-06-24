"""Stage 6 — Batch orchestrator: process a whole folder of clips in one command.

This is the daily-volume engine. It doesn't add new video logic — it chains the stages
that already exist, per clip:

    edit  ->  (branding, if assets exist)  ->  Shorts  ->  metadata (Stage 5, LLM)

Branding is skipped automatically while no intro/outro/logo assets exist; metadata is
skipped (not failed) when no Claude API key is configured. One bad clip is reported and
skipped without killing the rest of the batch.

Run it directly:
    python -m editor.pipeline input/hype/          # every clip in the folder
    python -m editor.pipeline clipA.mp4 clipB.mp4   # an explicit list
"""

import sys
from pathlib import Path

from editor.config import load_config
from editor.edit import edit
from editor.branding import brand
from editor.shorts import shorts
from editor.montage import montage, collect_clips
from editor.meta import generate_metadata
from editor.presets import detect_preset


def process_clip(clip: Path, make_shorts: bool, make_metadata: bool) -> dict:
    """Run one clip through edit -> (branding) -> Shorts -> metadata. Outcome dict."""
    out = {"clip": clip.name, "master": None, "branded": False,
           "short": None, "metadata": None}

    master = edit(str(clip))          # auto-picks music by preset
    out["master"] = master.name

    # Branding raises SystemExit when no intro/outro/logo is configured — that's the
    # normal "no brand yet" case, so treat it as "skip branding", not a failure.
    try:
        master = brand(str(master))
        out["branded"] = True
    except SystemExit as e:
        print(f"  (branding skipped: {e})")

    if make_shorts:
        out["short"] = shorts(str(master)).name

    # Metadata (Stage 5, LLM). Pass the original clip's preset through (the master now
    # lives in output/, where the folder no longer reveals it). A missing API key
    # raises SystemExit — treat that as "skip metadata", like branding, not a failure.
    if make_metadata:
        config = load_config()
        try:
            md_path, _thumb = generate_metadata(str(master), preset=detect_preset(clip, config))
            out["metadata"] = md_path.name
        except SystemExit as e:
            print(f"  (metadata skipped: {e})")

    return out


def run_batch(args: list[str]) -> list[dict]:
    """Process every clip from the args (a folder or a list). Returns per-clip outcomes."""
    config = load_config()
    batch_cfg = config.get("batch", {})
    make_shorts = bool(batch_cfg.get("make_shorts", True))
    make_metadata = bool(batch_cfg.get("make_metadata", True))

    clips, name = collect_clips(args)
    print(f"Batch: {len(clips)} clip(s) from '{name}'  "
          f"(shorts={'on' if make_shorts else 'off'}, "
          f"metadata={'on' if make_metadata else 'off'})\n")

    results = []
    for i, clip in enumerate(clips, 1):
        print(f"[{i}/{len(clips)}] {clip.name}")
        try:
            results.append(process_clip(clip, make_shorts, make_metadata))
        except (Exception, SystemExit) as e:   # noqa: BLE001 — isolate one clip's failure
            print(f"  ! FAILED: {e}")
            results.append({"clip": clip.name, "error": str(e)})
        print()

    if bool(batch_cfg.get("montage", False)):
        print("Building a montage of the batch...")
        try:
            montage(args)
        except (Exception, SystemExit) as e:   # noqa: BLE001
            print(f"  ! montage failed: {e}")

    # Summary.
    print("=== batch summary ===")
    for r in results:
        if "error" in r:
            print(f"  {r['clip']}: ERROR — {r['error']}")
        else:
            short = r["short"] or "(no short)"
            brand_tag = " +brand" if r["branded"] else ""
            meta_tag = " +meta" if r["metadata"] else ""
            print(f"  {r['clip']}: {r['master']}{brand_tag}  |  {short}{meta_tag}")
    return results


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m editor.pipeline <folder | clip1 clip2 ...>")
        print("  e.g. python -m editor.pipeline input/hype/")
        return 1
    run_batch(sys.argv[1:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
