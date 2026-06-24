"""Stage: voice.py — Audio-energy highlight detector for LoL clips.

Finds loud, action-packed moments without needing Whisper or any ML library.
Uses FFmpeg's ebur128 filter to measure momentary loudness (LUFS) every 100 ms.
In LoL, fights, kill sounds, and the in-game announcer all produce spikes that sit
far above idle gameplay noise — no speech recognition needed to find the highlights.

Output is compatible with detect.py's _moments.json format so highlights.py can
consume it without changes.  Use voice.py as a fast, zero-install alternative to
detect.py when you want action windows rather than specific announcer labels.

Writes a JSON sidecar:
    output/<name>_moments.json

    {
      "clip": "my_game.mp4",
      "duration": 64.2,
      "moments": [
        {"time": 23.4, "label": "audio_peak",
         "window_start": 15.4, "window_end": 27.4}
      ]
    }

Usage:
    python -m editor.voice input/my_game.mp4
    python -m editor.voice my_game.mp4   # bare name resolved from input/

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


def _loudness_samples(
    video: Path, stream_index: int = 0
) -> list[tuple[float, float]]:
    """Return (timestamp_s, momentary_lufs) pairs using FFmpeg's ebur128 filter.

    ebur128 measures Momentary loudness (100 ms window) in LUFS every 100 ms.
    Loud values are close to 0; near-silence is around −60 LUFS or lower.
    framelog=info prints per-frame measurements at the INFO log level so they
    appear in stderr without needing -v verbose.
    """
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner",
            "-i", str(video),
            "-map", f"0:a:{stream_index}",
            "-filter:a", "ebur128=framelog=info:peak=none",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    samples: list[tuple[float, float]] = []
    for line in result.stderr.splitlines():
        # e.g. [Parsed_ebur128_0 @ 0x...] t:  1.0000 TARGET:-23 M:-35.2 S:...
        m_t = re.search(r"\bt:\s*([\d.]+)", line)
        m_m = re.search(r"\bM:\s*(-?[\d.]+|-inf)", line)
        if not (m_t and m_m):
            continue
        t = float(m_t.group(1))
        raw = m_m.group(1)
        lufs = -120.0 if raw == "-inf" else float(raw)
        samples.append((t, lufs))
    return samples


def _find_moments(
    samples: list[tuple[float, float]],
    threshold_lufs: float,
    min_duration: float,
    merge_gap: float,
    window_before: float,
    window_after: float,
    clip_duration: float,
) -> list[dict]:
    """Group sustained loud 100 ms buckets into highlight moments."""
    if not samples:
        return []

    loud_times = [t for t, m in samples if m > threshold_lufs]
    if not loud_times:
        return []

    # Merge nearby timestamps into continuous loud segments.
    raw_segs: list[tuple[float, float]] = []
    seg_start = loud_times[0]
    seg_end = loud_times[0]
    for t in loud_times[1:]:
        if t - seg_end <= merge_gap:
            seg_end = t
        else:
            if seg_end - seg_start >= min_duration:
                raw_segs.append((seg_start, seg_end))
            seg_start = t
            seg_end = t
    if seg_end - seg_start >= min_duration:
        raw_segs.append((seg_start, seg_end))

    moments: list[dict] = []
    for start, end in raw_segs:
        # The midpoint of the loud burst is the "peak" timestamp.
        peak_t = round((start + end) / 2, 2)
        moments.append({
            "time": peak_t,
            "label": "audio_peak",
            "window_start": round(max(0.0, peak_t - window_before), 2),
            "window_end": round(min(clip_duration, peak_t + window_after), 2),
        })

    return moments


def detect_voice_moments(video: Path, config: dict) -> list[dict]:
    """Find audio-energy highlight moments in `video`."""
    cfg = config.get("voice", {})
    threshold_lufs = float(cfg.get("threshold_lufs", -18.0))
    min_duration   = float(cfg.get("min_duration", 1.0))
    merge_gap      = float(cfg.get("merge_gap", 2.0))
    window_before  = float(cfg.get("window_before", 8.0))
    window_after   = float(cfg.get("window_after", 4.0))
    audio_stream   = int(cfg.get("audio_stream", 0))

    print("  Measuring momentary loudness (ebur128) …")
    samples = _loudness_samples(video, stream_index=audio_stream)
    if not samples:
        print("  Warning: no audio samples returned.")
        print("  Make sure the clip has audio and FFmpeg can read it.")
        return []

    loud_count = sum(1 for _, m in samples if m > threshold_lufs)
    pct = 100 * loud_count / max(1, len(samples))
    print(f"  {len(samples)} samples — {loud_count} above {threshold_lufs} LUFS ({pct:.0f}%)")

    duration = probe_duration(video)
    return _find_moments(
        samples, threshold_lufs, min_duration, merge_gap,
        window_before, window_after, duration,
    )


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print("Usage: python -m editor.voice <clip>", file=sys.stderr)
        return 1

    config    = load_config()
    input_dir = ROOT / config["paths"]["input_dir"]
    out_dir   = ROOT / config["paths"]["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    video = _resolve(argv[0], input_dir)
    print(f"Detecting audio-energy moments in {video.name} …")

    moments = detect_voice_moments(video, config)
    duration = probe_duration(video)

    sidecar = out_dir / f"{video.stem}_moments.json"
    sidecar.write_text(
        json.dumps(
            {"clip": video.name, "duration": duration, "moments": moments},
            indent=2,
        ),
        encoding="utf-8",
    )

    if moments:
        print(f"\nFound {len(moments)} action moment(s):")
        for m in moments:
            print(f"  {m['time']:7.2f}s  [{m['label']:<14}]  "
                  f"window {m['window_start']}s – {m['window_end']}s")
    else:
        print("\nNo loud moments detected.")
        print("Tips: lower threshold_lufs in [voice] config (e.g. to -22) or")
        print("      check that the clip has game audio in the selected stream.")

    print(f"\nSidecar written: {sidecar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
