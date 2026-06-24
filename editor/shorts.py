"""Stage 3 — Shorts: reframe a 16:9 edit to a 9:16 vertical Short.

Input:  a 16:9 video (usually an _edited.mp4 from editor.edit)
Output: output/<name>_short.mp4

Uses a blurred-background fit (ADR 0005): the full game frame is scaled to the target
WIDTH and centered, so the minimap/HUD at the screen edges are never cropped; the empty
top and bottom are filled with a blurred, enlarged copy of the same frame. This is a
re-encode (not a stream copy). Audio is the already-balanced mix, copied untouched.

Run it directly:
    python -m editor.shorts output/my_game_edited.mp4
"""

import sys
from pathlib import Path

from editor.config import ROOT, load_config
from editor.ffmpeg import run


def _resolve_video(given: str) -> Path:
    """A real path, or a bare name found in output/ then input/."""
    p = Path(given)
    if p.exists():
        return p
    paths = load_config()["paths"]
    for d in (paths["output_dir"], paths["input_dir"]):
        alt = ROOT / d / given
        if alt.exists():
            return alt
    raise SystemExit(f"Video not found: {given} (looked in output/ and input/ too)")


def build_shorts_filter(w: int, h: int, blur: float) -> str:
    """filter_complex that fits the frame into w x h over a blurred background.

    bg: same frame scaled to COVER w x h (cropping the sides), then blurred.
    fg: same frame scaled to the full target WIDTH (nothing cropped), centered on bg.
    """
    return (
        "[0:v]split=2[bg][fg];"
        f"[bg]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},gblur=sigma={blur:.6g}[bgb];"
        f"[fg]scale={w}:-2[fgs];"
        # W/H/w/h here are FFmpeg overlay tokens (base + overlay sizes), not Python vars.
        "[bgb][fgs]overlay=(W-w)/2:(H-h)/2,format=yuv420p[vout]"
    )


def shorts(video_arg: str) -> Path:
    """Produce one 9:16 vertical Short. Returns the output path."""
    config = load_config()
    paths = config["paths"]
    shorts_cfg = config["shorts"]
    video_cfg = config["video"]

    video = _resolve_video(video_arg)

    res = str(shorts_cfg.get("resolution", "1080x1920")).strip()
    w, h = (int(x) for x in res.lower().split("x"))
    blur = float(shorts_cfg.get("blur", 20))

    graph = build_shorts_filter(w, h, blur)

    out_dir = ROOT / paths["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = video.stem[:-7] if video.stem.endswith("_edited") else video.stem
    out = out_dir / f"{stem}_short.mp4"

    args = [
        "-i", str(video),
        "-filter_complex", graph,
        "-map", "[vout]", "-map", "0:a?",      # keep the audio if present
        "-c:v", "libx264", "-crf", str(video_cfg["crf"]),
        "-preset", video_cfg["preset"], "-pix_fmt", "yuv420p",
        "-c:a", "copy",                        # audio unchanged -> copy (lossless, fast)
        "-movflags", "+faststart",
        str(out),
    ]

    print(f"Shorts {video.name}  ->  {out.name}   ({w}x{h}, blur sigma {blur:.6g})")
    run(args)
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m editor.shorts <video>")
        print("  e.g. python -m editor.shorts output/my_game_edited.mp4")
        return 1
    out = shorts(sys.argv[1])
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
