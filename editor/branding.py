"""Stage 2 — Branding: prepend an intro, append an outro, overlay a corner logo.

Input:  a video (usually an _edited.mp4 from editor.edit)
Output: output/<name>_branded.mp4

Everything is config-driven ([branding] in config.toml) and optional — leave any of
intro / outro / logo unset to skip that piece. The clips are joined with FFmpeg's
**concat filter** (not the stream-copy demuxer) so intro/outro of any resolution, fps,
or codec are normalized (scaled+padded, 48 kHz stereo) and join cleanly. The logo is
overlaid over the whole result. Intros are often silent, so clips without an audio
track get a matching length of silence injected, otherwise concat would fail.

Run it directly:
    python -m editor.branding output/my_game_edited.mp4
"""

import sys
from pathlib import Path

from editor.config import ROOT, load_config
from editor.ffmpeg import run, probe_video, probe_duration, has_audio

# overlay x:y expressions per corner; W/H = base video size, w/h = logo size, M = margin.
_CORNERS = {
    "top-left": "{M}:{M}",
    "top-right": "W-w-{M}:{M}",
    "bottom-left": "{M}:H-h-{M}",
    "bottom-right": "W-w-{M}:H-h-{M}",
}


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


def _asset(name: str, assets_dir: Path) -> Path | None:
    """Resolve an optional asset by name; warn-and-skip if set but missing."""
    if not str(name).strip():
        return None
    p = assets_dir / name
    if not p.exists():
        print(f"  ! branding asset not found, skipping: {p}")
        return None
    return p


def build_branding_filter(clips, w, h, fps, logo, logo_opts) -> tuple[str, str, str]:
    """Build the filter_complex. Returns (graph, video_label, audio_label)."""
    parts = []
    segments = []
    for i, clip in enumerate(clips):
        # Normalize each clip to the same canvas: fit-and-pad keeps aspect (letterbox
        # if an intro is a different shape), then fixed fps + pixel format.
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
            # Silent clip: synthesize matching-length silence so concat stays aligned.
            parts.append(
                f"anullsrc=channel_layout=stereo:sample_rate=48000,"
                f"atrim=duration={probe_duration(clip):.3f},"
                f"aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]"
            )
        segments.append(f"[v{i}][a{i}]")

    n = len(clips)
    parts.append(f"{''.join(segments)}concat=n={n}:v=1:a=1[cv][ca]")

    if logo is None:
        return ";".join(parts), "[cv]", "[ca]"

    logo_idx = n  # the logo is the -i input right after all the clips
    chain = f"[{logo_idx}:v]scale={logo_opts['width']}:-1"
    if logo_opts["opacity"] < 1.0:
        chain += f",format=rgba,colorchannelmixer=aa={logo_opts['opacity']}"
    chain += "[logo]"
    parts.append(chain)
    pos = _CORNERS[logo_opts["corner"]].format(M=logo_opts["margin"])
    parts.append(f"[cv][logo]overlay={pos}[outv]")
    return ";".join(parts), "[outv]", "[ca]"


def brand(video_arg: str) -> Path:
    """Apply intro/outro/logo branding to a video. Returns the output path."""
    config = load_config()
    paths = config["paths"]
    branding = config["branding"]
    video_cfg = config["video"]

    video = _resolve_video(video_arg)
    assets_dir = ROOT / paths["assets_dir"]
    intro = _asset(branding.get("intro", ""), assets_dir)
    outro = _asset(branding.get("outro", ""), assets_dir)
    logo = _asset(branding.get("logo", ""), assets_dir)

    if intro is None and outro is None and logo is None:
        raise SystemExit(
            "No branding assets configured (intro/outro/logo all unset or missing). "
            "Set them under [branding] in config.toml and put the files in assets/."
        )

    # Target canvas: explicit [video] settings win, else take the main clip's own size/fps.
    main = probe_video(video)
    res = str(video_cfg.get("resolution", "")).strip()
    if res:
        w, h = (int(x) for x in res.lower().split("x"))
    else:
        w, h = main["width"], main["height"]
    fps = float(video_cfg.get("fps", 0) or 0) or main["fps"]

    clips = [c for c in (intro, video, outro) if c is not None]
    logo_opts = {
        "width": int(branding.get("logo_width", 160)),
        "opacity": float(branding.get("logo_opacity", 1.0)),
        "corner": branding.get("logo_corner", "top-right"),
        "margin": int(branding.get("logo_margin", 24)),
    }
    graph, vout, aout = build_branding_filter(clips, w, h, fps, logo, logo_opts)

    out_dir = ROOT / paths["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = video.stem[:-7] if video.stem.endswith("_edited") else video.stem
    out = out_dir / f"{stem}_branded.mp4"

    args = []
    for clip in clips:
        args += ["-i", str(clip)]
    if logo is not None:
        args += ["-i", str(logo)]
    args += [
        "-filter_complex", graph,
        "-map", vout, "-map", aout,
        "-c:v", "libx264", "-crf", str(video_cfg["crf"]),
        "-preset", video_cfg["preset"], "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(out),
    ]

    pieces = [p.name for p in (intro, video, outro) if p is not None]
    print(f"Branding {video.name}  ->  {out.name}")
    print(f"  sequence: {' + '.join(pieces)}"
          f"{'   logo: ' + logo.name if logo else '   (no logo)'}  @ {w}x{h} {fps:.6g}fps")
    run(args)
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m editor.branding <video>")
        print("  e.g. python -m editor.branding output/my_game_edited.mp4")
        print("  Reads intro/outro/logo from [branding] in config.toml (all optional).")
        return 1
    out = brand(sys.argv[1])
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
