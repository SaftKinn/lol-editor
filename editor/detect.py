"""Stage: detect.py — LoL announcer keyword detection via Whisper.

Finds highlight moments (Double Kill, Pentakill, Ace, First Blood, …) in a raw
gameplay clip by transcribing the game audio and matching fixed announcer phrases.

Writes a JSON sidecar next to the output folder:
    output/<name>_moments.json
    {
      "clip": "my_game.mp4",
      "duration": 64.2,
      "moments": [
        {"time": 23.4, "label": "pentakill",
         "window_start": 13.4, "window_end": 28.4}
      ]
    }

Run this on the RAW clip (before edit.py), so the game audio is not yet mixed
with music — the announcer voice is cleanest at that point.

Usage:
    python -m editor.detect input/my_game.mp4
    python -m editor.detect my_game.mp4        # bare name resolved from input/

Requires (one-time install — not needed for the rest of the pipeline):
    pip install faster-whisper
"""

import json
import sys
import tempfile
from pathlib import Path

from editor.config import ROOT, load_config
from editor.ffmpeg import probe_duration, run as ff_run

try:
    from faster_whisper import WhisperModel
    _WHISPER_OK = True
except ImportError:
    _WHISPER_OK = False


# Built-in LoL announcer phrases → label. Lower-case; Whisper output is lowercased
# before matching. Whisper may spell "Penta Kill" or "pentakill" — both forms listed.
_KEYWORDS: dict[str, str] = {
    "first blood":   "first_blood",
    "double kill":   "double_kill",
    "triple kill":   "triple_kill",
    "quadra kill":   "quadra_kill",
    "penta kill":    "pentakill",
    "pentakill":     "pentakill",
    "ace":           "ace",
    "shutdown":      "shutdown",
    "legendary":     "legendary",
    "godlike":       "godlike",
    "unstoppable":   "unstoppable",
    "dominating":    "dominating",
    "baron slain":   "baron",
    "dragon slain":  "dragon",
    "inhibitor":     "inhibitor",
}


def _resolve(given: str, default_dir: Path) -> Path:
    """Accept either a real path or a bare name living in the default folder."""
    p = Path(given)
    if p.exists():
        return p
    alt = default_dir / given
    if alt.exists():
        return alt
    raise SystemExit(f"File not found: {given} (also looked in {default_dir})")


def _extract_wav(video: Path, wav: Path, stream_index: int = 0) -> None:
    """Dump one audio stream to a mono 16 kHz WAV — the format Whisper expects."""
    ff_run([
        "-i", str(video),
        "-map", f"0:a:{stream_index}",
        "-ac", "1",           # mono
        "-ar", "16000",       # 16 kHz
        str(wav),
    ])


def detect_moments(video: Path, config: dict) -> list[dict]:
    """Transcribe `video` and return a list of detected highlight moments.

    Each moment: {"time": float, "label": str, "window_start": float, "window_end": float}
    """
    cfg = config.get("detect", {})
    model_size    = str(cfg.get("model", "base"))
    device        = str(cfg.get("device", "cpu"))
    window_before = float(cfg.get("window_before", 10))
    window_after  = float(cfg.get("window_after", 5))
    extra         = {kw.lower(): kw.lower().replace(" ", "_")
                     for kw in cfg.get("keywords", [])}

    keywords = {**_KEYWORDS, **extra}
    duration = probe_duration(video)

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        print("  Extracting game audio …")
        _extract_wav(video, wav)

        compute = "float16" if device == "cuda" else "int8"
        print(f"  Loading Whisper '{model_size}' on {device} …")
        model = WhisperModel(model_size, device=device, compute_type=compute)

        print("  Transcribing …")
        segments, _ = model.transcribe(str(wav), language="en")

        moments: list[dict] = []
        seen: set[tuple] = set()
        for seg in segments:
            text = seg.text.lower()
            for phrase, label in keywords.items():
                if phrase in text:
                    key = (label, round(seg.start, 0))   # dedupe ~same second
                    if key in seen:
                        continue
                    seen.add(key)
                    t = round(seg.start, 2)
                    moments.append({
                        "time":         t,
                        "label":        label,
                        "window_start": round(max(0.0, t - window_before), 2),
                        "window_end":   round(min(duration, t + window_after), 2),
                    })

    return sorted(moments, key=lambda m: m["time"])


def main(argv: list[str] | None = None) -> int:
    if not _WHISPER_OK:
        print(
            "detect.py needs faster-whisper — install it once with:\n"
            "    pip install faster-whisper\n\n"
            "The rest of the pipeline works without it.",
            file=sys.stderr,
        )
        return 1

    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print("Usage: python -m editor.detect <clip>", file=sys.stderr)
        return 1

    config    = load_config()
    input_dir = ROOT / config["paths"]["input_dir"]
    out_dir   = ROOT / config["paths"]["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    video = _resolve(argv[0], input_dir)
    print(f"Detecting highlight moments in {video.name} …")

    moments = detect_moments(video, config)

    duration = probe_duration(video)
    sidecar  = out_dir / f"{video.stem}_moments.json"
    sidecar.write_text(
        json.dumps({"clip": video.name, "duration": duration, "moments": moments}, indent=2),
        encoding="utf-8",
    )

    if moments:
        print(f"\nFound {len(moments)} moment(s):")
        for m in moments:
            print(f"  {m['time']:7.2f}s  [{m['label']:<14}]  "
                  f"window {m['window_start']}s – {m['window_end']}s")
    else:
        print("\nNo announcer keywords detected in this clip.")

    print(f"\nSidecar written: {sidecar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
