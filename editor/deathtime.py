"""Stage: deathtime.py — Detect death-screen segments in a LoL clip.

Analyses frame brightness at low frame-rate using FFmpeg's signalstats filter.
In LoL, when you die the screen dims noticeably — a sustained brightness drop below
the clip's own baseline marks the time you are waiting to respawn.  Knowing these
windows lets you cut dead time from clips to keep them action-packed.

Writes a JSON sidecar:
    output/<name>_deathsegs.json
    {
      "clip": "my_game.mp4",
      "duration": 64.2,
      "segments": [
        {"start": 10.5, "end": 38.2, "duration_s": 27.7}
      ]
    }

Usage:
    python -m editor.deathtime input/my_game.mp4
    python -m editor.deathtime my_game.mp4   # bare name resolved from input/

No extra pip installs — uses FFmpeg only.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from editor.config import ROOT, load_config
from editor.ffmpeg import probe_duration


def _resolve(given: str, default_dir: Path) -> Path:
    p = Path(given)
    if p.exists():
        return p
    alt = default_dir / given
    if alt.exists():
        return alt
    raise SystemExit(f"File not found: {given} (also looked in {default_dir})")


def _sample_brightness(video: Path, sample_fps: float) -> list[tuple[float, float]]:
    """Return (timestamp_s, yavg) pairs sampled from the video at sample_fps.

    Uses FFmpeg's signalstats filter with metadata=print:file=- so the per-frame
    stats come out on stdout in the form:
        frame:N  pts:X  pts_time:Y
        lavfi.signalstats.YAVG=87.23
        ...
    YAVG is the mean luma of a frame (0–255).  Lower = darker.
    """
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner",
            "-i", str(video),
            "-vf", f"fps={sample_fps},signalstats,metadata=print:file=-",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    samples: list[tuple[float, float]] = []
    current_t: float | None = None
    for line in result.stdout.splitlines():
        # Frame header line: "frame:N  pts:X  pts_time:Y"
        m_t = re.search(r"pts_time:([\d.]+)", line)
        if m_t:
            current_t = float(m_t.group(1))
            continue
        # Stat line: "lavfi.signalstats.YAVG=87.23"
        m_y = re.match(r"lavfi\.signalstats\.YAVG=([\d.]+)", line)
        if m_y and current_t is not None:
            samples.append((round(current_t, 2), float(m_y.group(1))))
    return samples


def _group_segments(
    dark_times: list[float],
    interval: float,
    merge_gap: float,
    min_duration: float,
    clip_duration: float,
) -> list[dict]:
    """Merge nearby dark-frame timestamps into death segments.

    dark_times — timestamps (seconds) of frames flagged as dark.
    Returns [{"start": float, "end": float, "duration_s": float}].
    """
    if not dark_times:
        return []

    segments: list[dict] = []
    seg_start = dark_times[0]
    seg_end = dark_times[0] + interval

    for t in dark_times[1:]:
        if t - seg_end <= merge_gap:
            seg_end = t + interval
        else:
            if seg_end - seg_start >= min_duration:
                end = round(min(seg_end, clip_duration), 2)
                segments.append({
                    "start": round(seg_start, 2),
                    "end": end,
                    "duration_s": round(end - seg_start, 2),
                })
            seg_start = t
            seg_end = t + interval

    if seg_end - seg_start >= min_duration:
        end = round(min(seg_end, clip_duration), 2)
        segments.append({
            "start": round(seg_start, 2),
            "end": end,
            "duration_s": round(end - seg_start, 2),
        })

    return segments


def detect_death_segments(video: Path, config: dict) -> list[dict]:
    """Analyse `video` and return a list of detected death-screen segments."""
    cfg = config.get("deathtime", {})
    sample_fps    = float(cfg.get("sample_fps", 2.0))
    dark_threshold = float(cfg.get("dark_threshold", 0.80))
    min_duration  = float(cfg.get("min_duration", 5.0))
    merge_gap     = float(cfg.get("merge_gap", 2.0))

    print("  Sampling frame brightness …")
    samples = _sample_brightness(video, sample_fps)
    if not samples:
        print("  Warning: no frame data returned — check that FFmpeg can read the clip.")
        return []

    # Use the 75th-percentile YAVG as baseline (robust to brief dark scenes at clip edges).
    yavgs = sorted(s[1] for s in samples)
    baseline = yavgs[int(len(yavgs) * 0.75)]
    cutoff = baseline * dark_threshold
    print(f"  Brightness baseline (p75 YAVG): {baseline:.1f}  |  dark cutoff: {cutoff:.1f}")

    dark_times = [t for t, y in samples if y < cutoff]
    pct = 100 * len(dark_times) / max(1, len(samples))
    print(f"  Dark frames: {len(dark_times)} / {len(samples)} ({pct:.0f}%)")

    duration = probe_duration(video)
    return _group_segments(dark_times, 1.0 / sample_fps, merge_gap, min_duration, duration)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print("Usage: python -m editor.deathtime <clip>", file=sys.stderr)
        return 1

    config    = load_config()
    input_dir = ROOT / config["paths"]["input_dir"]
    out_dir   = ROOT / config["paths"]["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    video = _resolve(argv[0], input_dir)
    print(f"Detecting death-screen segments in {video.name} …")

    segments = detect_death_segments(video, config)
    duration = probe_duration(video)

    sidecar = out_dir / f"{video.stem}_deathsegs.json"
    sidecar.write_text(
        json.dumps(
            {"clip": video.name, "duration": duration, "segments": segments},
            indent=2,
        ),
        encoding="utf-8",
    )

    if segments:
        dead_total = sum(s["duration_s"] for s in segments)
        print(f"\nFound {len(segments)} death segment(s) — {dead_total:.1f}s of dead time:")
        for seg in segments:
            print(f"  {seg['start']:6.1f}s – {seg['end']:6.1f}s  ({seg['duration_s']:.1f}s)")
    else:
        print("\nNo death segments detected in this clip.")
        print("(If you're testing on a Medal clip, it's likely already cut to the action —")
        print(" try on a full-game recording instead.)")

    print(f"\nSidecar written: {sidecar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
