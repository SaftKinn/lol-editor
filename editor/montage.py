"""Stage 4 — Montage: stitch several clips into one long-form highlight video.

Input:  several clips, or a folder of clips
Output: output/<name>_montage.mp4

Long-form is the higher-CPM format (the revenue side; Shorts are the funnel). Clips are
joined with the FFmpeg concat filter (each normalized to one canvas, like branding) so
mixed-format clips just work. For consistent audio across the cuts, one royalty-free
track is laid under the whole montage — picked from the clips' preset pool and ducked +
normalized with the same logic as the core edit (config [montage].music_bed). With the
bed off, each clip keeps its own audio.

Run it directly:
    python -m editor.montage input/hype/          # all clips in the folder, in order
    python -m editor.montage clip1.mp4 clip2.mp4   # an explicit ordered list
"""

import sys
from pathlib import Path

from editor.config import ROOT, load_config
from editor.ffmpeg import run, probe_video, probe_duration, has_audio
from editor.edit import build_audio_filter
from editor.presets import choose_music

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


def _resolve_clip(given: str) -> Path:
    """A real path, or a bare name found in input/ then output/."""
    p = Path(given)
    if p.exists():
        return p
    paths = load_config()["paths"]
    for d in (paths["input_dir"], paths["output_dir"]):
        alt = ROOT / d / given
        if alt.exists():
            return alt
    raise SystemExit(f"Clip not found: {given} (looked in input/ and output/ too)")


def collect_clips(args: list[str]) -> tuple[list[Path], str]:
    """Resolve CLI args into an ordered clip list + a name for the output file.

    A single folder arg -> every video in it (sorted). Otherwise each arg is a clip.
    """
    if len(args) == 1:
        folder = Path(args[0])
        if not folder.is_dir():
            folder = ROOT / args[0]
        if folder.is_dir():
            clips = sorted(p for p in folder.iterdir()
                           if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS)
            if not clips:
                raise SystemExit(f"No video clips found in {folder}")
            return clips, folder.name
    return [_resolve_clip(a) for a in args], "montage"


def build_montage_filter(clips, w, h, fps, audio_cfg, with_music) -> tuple[str, str, str]:
    """Build the filter_complex. Returns (graph, video_label, audio_label).

    When `with_music`, the music input is the clip right after the last clip
    (index len(clips)); the concatenated game audio is mixed under a ducked bed.
    """
    parts = []
    segments = []
    for i, clip in enumerate(clips):
        parts.append(
            f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,"
            f"fps={fps:.6g},format=yuv420p[v{i}]"
        )
        if has_audio(clip):
            parts.append(
                f"[{i}:a]aresample=48000,"
                f"aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]"
            )
        else:
            parts.append(
                f"anullsrc=channel_layout=stereo:sample_rate=48000,"
                f"atrim=duration={probe_duration(clip):.3f},"
                f"aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]"
            )
        segments.append(f"[v{i}][a{i}]")

    n = len(clips)
    parts.append(f"{''.join(segments)}concat=n={n}:v=1:a=1[cv][cg]")

    if with_music:
        # Reuse the core edit's ducking + loudness, reading the concatenated game
        # audio [cg] and the looped music input [n:a].
        parts.append(build_audio_filter(
            float(audio_cfg["music_volume"]), bool(audio_cfg["duck_music"]),
            float(audio_cfg["target_loudness"]),
            game="[cg]", music=f"[{n}:a]", out="[aout]",
        ))
        return ";".join(parts), "[cv]", "[aout]"

    return ";".join(parts), "[cv]", "[cg]"


def _pick_bed(clips: list[Path], config: dict, out_stem: str) -> Path | None:
    """Pick one music bed from the clips' preset pool; None if none available."""
    # choose_music keys off the file name, so use the output name for a stable pick
    # while detecting the preset from the first clip's folder.
    probe = clips[0].with_name(out_stem + clips[0].suffix)
    try:
        return choose_music(probe, config)
    except SystemExit as e:
        print(f"  ! {e}  -> montage will keep each clip's own audio.")
        return None


def montage(args: list[str]) -> Path:
    """Stitch clips into one long-form video. Returns the output path."""
    config = load_config()
    paths = config["paths"]
    video_cfg = config["video"]
    audio_cfg = config["audio"]
    montage_cfg = config.get("montage", {})

    clips, name = collect_clips(args)
    if len(clips) < 2:
        print(f"  ! only {len(clips)} clip — a montage usually stitches several.")

    out_dir = ROOT / paths["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{name}_montage.mp4"

    # Target canvas from the first clip (or explicit [video] settings).
    first = probe_video(clips[0])
    res = str(video_cfg.get("resolution", "")).strip()
    if res:
        w, h = (int(x) for x in res.lower().split("x"))
    else:
        w, h = first["width"], first["height"]
    fps = float(video_cfg.get("fps", 0) or 0) or first["fps"]

    bed = _pick_bed(clips, config, out.stem) if bool(montage_cfg.get("music_bed", True)) else None
    graph, vmap, amap = build_montage_filter(clips, w, h, fps, audio_cfg, bed is not None)

    args_ff = []
    for clip in clips:
        args_ff += ["-i", str(clip)]
    if bed is not None:
        args_ff += ["-stream_loop", "-1", "-i", str(bed)]   # loop the bed over the montage
    args_ff += [
        "-filter_complex", graph,
        "-map", vmap, "-map", amap,
        "-c:v", "libx264", "-crf", str(video_cfg["crf"]),
        "-preset", video_cfg["preset"], "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(out),
    ]

    bed_label = bed.name if bed else "(none — keeping each clip's own audio)"
    print(f"Montage of {len(clips)} clip(s)  ->  {out.name}   @ {w}x{h} {fps:.6g}fps")
    print(f"  clips: {', '.join(c.name for c in clips)}")
    print(f"  music bed: {bed_label}")
    run(args_ff)
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m editor.montage <folder | clip1 clip2 ...>")
        print("  e.g. python -m editor.montage input/hype/")
        print("       python -m editor.montage clipA.mp4 clipB.mp4")
        return 1
    out = montage(sys.argv[1:])
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
