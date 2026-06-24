"""Stage 6 — Batch orchestrator: process a whole folder of clips in one command.

This is the daily-volume engine. It doesn't add new video logic — it chains the stages
that already exist, per clip:

    edit  ->  (branding, if assets exist)  ->  Shorts

Metadata (Stage 5, the LLM) is not built yet, so it's reported as pending rather than run.
Branding is skipped automatically while no intro/outro/logo assets exist. One bad clip is
reported and skipped without killing the rest of the batch.

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


def process_clip(clip: Path, make_shorts: bool) -> dict:
    """Run one clip through edit -> (branding) -> Shorts. Returns an outcome dict."""
    out = {"clip": clip.name, "master": None, "branded": False, "short": None}

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

    return out


def run_batch(args: list[str]) -> list[dict]:
    """Process every clip from the args (a folder or a list). Returns per-clip outcomes."""
    config = load_config()
    batch_cfg = config.get("batch", {})
    make_shorts = bool(batch_cfg.get("make_shorts", True))

    clips, name = collect_clips(args)
    print(f"Batch: {len(clips)} clip(s) from '{name}'  "
          f"(shorts={'on' if make_shorts else 'off'})\n")

    results = []
    for i, clip in enumerate(clips, 1):
        print(f"[{i}/{len(clips)}] {clip.name}")
        try:
            results.append(process_clip(clip, make_shorts))
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
            print(f"  {r['clip']}: {r['master']}{brand_tag}  |  {short}")
    print("  metadata (title/tags/description/thumbnail): pending Phase 5 (LLM).")
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
