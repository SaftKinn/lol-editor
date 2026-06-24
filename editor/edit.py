"""Core edit: balance one gameplay video against one music track, export upload-ready.

Input:  a gameplay video + a royalty-free music track
Output: output/<video-name>_edited.mp4

What it does (all deterministic FFmpeg):
  - keeps the gameplay audio in front,
  - lays the music underneath at a configurable level, looped to the video's length,
  - optionally DUCKS the music (auto-quiets it when the game gets loud) via sidechain
    compression, so kills/fights always sit on top,
  - normalizes the final mix to YouTube's reference loudness,
  - copies the video stream untouched (lossless, fast) unless you ask for a resize/fps.

Run it directly:
    python -m editor.edit input/my_game.mp4 music/my_track.mp3

This is the foundation the other jobs (Shorts, montage, overlays) build on.
"""

import sys
from pathlib import Path

from editor.config import ROOT, load_config
from editor.ffmpeg import run
from editor.presets import choose_music


def _resolve(given: str, default_dir: Path) -> Path:
    """Accept either a real path or a bare name living in the default folder."""
    p = Path(given)
    if p.exists():
        return p
    alt = default_dir / given
    if alt.exists():
        return alt
    raise SystemExit(f"File not found: {given} (looked in {default_dir} too)")


def build_audio_filter(
    music_volume: float,
    duck: bool,
    target_loudness: float,
    game: str = "[0:a]",
    music: str = "[1:a]",
    out: str = "[aout]",
) -> str:
    """FFmpeg filter_complex mixing a gameplay audio source + a music source -> out.

    `game` / `music` / `out` are the filtergraph labels to read from / write to. The
    defaults wire it for the core edit (gameplay = input 0, music = input 1). The
    montage stage passes its own labels to reuse the exact same ducking + normalize.
    """
    # Everything resampled to 48 kHz so the filters line up cleanly.
    if duck:
        # Split gameplay: one copy feeds the mix, one is the sidechain key that
        # tells the compressor when to duck the music.
        return (
            f"{game}aresample=48000,asplit=2[ga][gkey];"
            f"{music}aresample=48000,volume={music_volume}[bg];"
            "[bg][gkey]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[bgduck];"
            "[ga][bgduck]amix=inputs=2:duration=first:normalize=0[mix];"
            # loudnorm resamples internally and can emit an odd rate, so force 48 kHz back.
            f"[mix]loudnorm=I={target_loudness}:TP=-1.5:LRA=11,aresample=48000{out}"
        )
    return (
        f"{game}aresample=48000[ga];"
        f"{music}aresample=48000,volume={music_volume}[bg];"
        "[ga][bg]amix=inputs=2:duration=first:normalize=0[mix];"
        f"[mix]loudnorm=I={target_loudness}:TP=-1.5:LRA=11,aresample=48000{out}"
    )


def edit(video_arg: str, music_arg: str | None = None) -> Path:
    """Produce one upload-ready edited video. Returns the output path.

    If `music_arg` is omitted, the music track is chosen automatically from the
    pool matching the clip's preset (its input sub-folder) — see editor/presets.py.
    """
    config = load_config()
    paths = config["paths"]
    audio = config["audio"]
    video_cfg = config["video"]

    video = _resolve(video_arg, ROOT / paths["input_dir"])
    if music_arg:
        music = _resolve(music_arg, ROOT / paths["music_dir"])
    else:
        music = choose_music(video, config)

    out_dir = ROOT / paths["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{video.stem}_edited.mp4"

    # Build the video half of the graph only if a resize/fps change is requested;
    # otherwise we copy the video stream untouched (lossless + fast).
    resolution = str(video_cfg.get("resolution", "")).strip()
    fps = int(video_cfg.get("fps", 0) or 0)
    vf = []
    if resolution:
        w, h = resolution.lower().split("x")
        vf.append(f"scale={w}:{h}")
    if fps:
        vf.append(f"fps={fps}")
    reencode = bool(vf)

    audio_graph = build_audio_filter(
        float(audio["music_volume"]), bool(audio["duck_music"]), float(audio["target_loudness"])
    )
    video_graph = f"[0:v]{','.join(vf)}[v];" if vf else ""
    filtergraph = video_graph + audio_graph

    args = [
        "-i", str(video),
        "-stream_loop", "-1", "-i", str(music),   # loop the music to cover the video
        "-filter_complex", filtergraph,
    ]
    if reencode:
        args += [
            "-map", "[v]",
            "-c:v", "libx264", "-crf", str(video_cfg["crf"]),
            "-preset", video_cfg["preset"], "-pix_fmt", "yuv420p",
        ]
    else:
        args += ["-map", "0:v", "-c:v", "copy"]
    args += [
        "-map", "[aout]", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(out),
    ]

    print(f"Editing {video.name}  +  {music.name}  ->  {out.name}")
    print(f"  music_volume={audio['music_volume']}  duck={audio['duck_music']}  "
          f"loudness={audio['target_loudness']} LUFS  video={'re-encode' if reencode else 'copy'}")
    run(args)
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m editor.edit <gameplay-video> [music-track]")
        print("  explicit music: python -m editor.edit input/my_game.mp4 music/my_track.mp3")
        print("  auto by preset: python -m editor.edit input/hype/my_game.mp4")
        print("    (music is picked from music/<preset>/ based on the input sub-folder)")
        return 1
    music_arg = sys.argv[2] if len(sys.argv) > 2 else None
    out = edit(sys.argv[1], music_arg)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
