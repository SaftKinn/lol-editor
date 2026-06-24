"""Stage 5 — Discovery: English metadata + a thumbnail for one finished video.

Input:  a finished video (usually an output/<name>_edited.mp4 master)
Output: output/<name>_metadata.md    (human-readable packet to paste into YouTube)
        output/<name>_metadata.json  (the raw fields, for later automation)
        output/<name>_thumb.png       (a frame from the video + bold overlay text)

Deterministic vs. creative split (ADR 0001):
  - the LLM writes the creative TEXT — titles, tags, descriptions, thumbnail wording,
  - CODE does everything else: grabbing the thumbnail frame (FFmpeg), laying the text
    out as Markdown, burning the overlay. The LLM never sets a timing or does math.

This is the only stage that talks to the cloud. We call the Claude API directly over
HTTPS with the standard library (urllib) — no third-party SDK, matching the project's
"no third-party dependencies" rule. The model + key are config-driven ([llm]); the key
is read from an environment variable so it never lands in git.

We have no transcript or frame analysis yet (that is Part 2 / ADR 0006), so the LLM is
given the clip's preset, file name and duration and asked to write engaging League of
Legends highlight metadata that fits the channel identity.

Run it directly:
    python -m editor.meta output/my_game_edited.mp4
    python -m editor.meta my_game_edited.mp4        # bare name, resolved in output/
"""

import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from editor.config import ROOT, load_config
from editor.edit import _resolve
from editor.ffmpeg import probe_duration, run
from editor.presets import detect_preset

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# Title caps kept under the hard limit so feeds don't truncate them.
YOUTUBE_TITLE_MAX = 100   # hard cap; aim for <= 70

# A loose hint per preset so the LLM matches the right energy.
PRESET_HINTS = {
    "hype": "high-energy plays, highlights and outplays",
    "funny": "funny, chaotic or unlucky moments",
}

# JSON shape we force the model to return: one block per surface we publish to,
# plus the short thumbnail wording. Structured output guarantees valid JSON.
METADATA_SCHEMA = {
    "type": "object",
    "properties": {
        "youtube_long": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "description", "tags"],
            "additionalProperties": False,
        },
        "youtube_short": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "hashtags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "description", "hashtags"],
            "additionalProperties": False,
        },
        "thumbnail_text": {"type": "string"},
    },
    "required": ["youtube_long", "youtube_short", "thumbnail_text"],
    "additionalProperties": False,
}


# --- API key + Claude call (the only cloud part) ------------------------------

def _read_env_file(path: Path, var: str) -> str:
    """Pull one KEY=VALUE out of a .env-style file (so we can reuse an existing key)."""
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == var:
            return value.strip().strip('"').strip("'")
    return ""


def load_api_key(config: dict) -> str:
    """Find the Claude API key: environment variable first, then optional env_file."""
    llm = config.get("llm", {})
    var = str(llm.get("api_key_env", "ANTHROPIC_API_KEY"))
    key = os.environ.get(var, "").strip()
    if not key:
        env_file = str(llm.get("env_file", "")).strip()
        if env_file:
            key = _read_env_file(Path(env_file), var)
    if not key or key.startswith("your-"):
        raise SystemExit(
            f"No Claude API key found. Set {var} in your environment, or point "
            f"[llm].env_file at a file that defines it."
        )
    return key


def call_claude(config: dict, prompt: str, schema: dict) -> dict:
    """POST one prompt to the Claude API and return the schema-validated JSON reply."""
    llm = config["llm"]
    body = {
        "model": llm["model"],
        "max_tokens": int(llm.get("max_tokens", 2000)),
        "messages": [{"role": "user", "content": prompt}],
        # Structured outputs: the model is constrained to our schema, so the reply's
        # first text block is guaranteed-valid JSON (no fragile prompt-parsing).
        "output_config": {"format": {"type": "json_schema", "schema": schema}},
    }
    request = urllib.request.Request(
        ANTHROPIC_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": load_api_key(config),
            "anthropic-version": ANTHROPIC_VERSION,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Claude API error {exc.code}: {exc.read().decode('utf-8', 'replace')}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach the Claude API: {exc.reason}")

    text = "".join(b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text")
    if not text:
        raise SystemExit(f"Claude returned no text content: {payload}")
    return json.loads(text)


# --- Prompt + Markdown rendering ----------------------------------------------

def build_llm_prompt(video_name: str, preset: str | None, duration_s: float) -> str:
    """Ask the LLM for English YouTube metadata in the channel's voice."""
    hint = PRESET_HINTS.get(preset or "", "League of Legends highlights")
    preset_label = preset or "general"
    return (
        "You write YouTube metadata for a League of Legends highlights channel. The channel "
        "posts hype highlight edits and funny moments with a Darius-main and ARAM-chaos "
        "identity. Audience-facing text is ENGLISH and aimed at growth and monetization: "
        "punchy and engaging for a gaming audience, but honest — no false claims, no ALL CAPS "
        "in titles, no emojis in titles.\n\n"
        f"CLIP FILE: {video_name}\n"
        f"PRESET: {preset_label} ({hint})\n"
        f"DURATION: about {duration_s:.0f} seconds\n\n"
        "You do NOT have a transcript or the video frames. Write engaging League of Legends "
        "highlight metadata that fits the preset and channel identity. Use the clip file name "
        "only as a loose hint (it may name a champion or game mode).\n\n"
        "Produce metadata for two surfaces:\n"
        "1. youtube_long  — the 16:9 highlight video.\n"
        "2. youtube_short — a 9:16 Shorts cut of the same clip.\n\n"
        "RULES\n"
        f"- Titles: compelling for a gaming audience, at most {YOUTUBE_TITLE_MAX} characters "
        "(aim under 70), no emojis, no ALL CAPS.\n"
        "- youtube_long.description: 2-4 short paragraphs. Open with a 1-sentence hook, then a "
        "line on what the viewer sees, and end with a short, generic invite to subscribe. "
        "Plain text, no markdown.\n"
        "- youtube_short.description: 1 sentence.\n"
        "- tags (youtube_long only): 10-15 plain keyword phrases, NO '#' symbol.\n"
        "- hashtags (youtube_short): 5-10 items, each a single word or joined phrase with NO "
        "spaces and NO '#' (it is added automatically).\n"
        "- thumbnail_text: 2-4 punchy UPPERCASE words for a thumbnail overlay "
        "(e.g. 'DARIUS GOES OFF'), short enough to read at a glance.\n"
    )


def _hashtag_line(hashtags: list[str]) -> str:
    """Turn ['darius','aram'] into '#darius #aram'. Deterministic = code."""
    clean = [tag.lstrip("#").replace(" ", "") for tag in hashtags if tag.strip()]
    return " ".join(f"#{tag}" for tag in clean)


def render_metadata_md(video_name: str, data: dict) -> str:
    """Lay the LLM's metadata fields out as a paste-ready Markdown packet (code)."""
    yl = data["youtube_long"]
    ys = data["youtube_short"]
    return (
        f"# Metadata — {video_name}\n\n"
        "> Generated by LoL Editor (Stage 5). Copy each block into the YouTube upload form.\n"
        "> Audience-facing text is English (ADR 0003). Music is royalty-free — no AI-voice "
        "disclosure needed.\n\n"
        "## YouTube — long form (16:9)\n\n"
        f"**Title** ({len(yl['title'])} chars)\n\n{yl['title']}\n\n"
        f"**Description**\n\n{yl['description']}\n\n"
        f"**Tags**\n\n{', '.join(yl['tags'])}\n\n"
        "---\n\n"
        "## YouTube — Shorts (9:16)\n\n"
        f"**Title** ({len(ys['title'])} chars)\n\n{ys['title']}\n\n"
        f"**Description**\n\n{ys['description']}\n\n"
        f"**Hashtags**\n\n{_hashtag_line(ys['hashtags'])} #Shorts\n\n"
        "---\n\n"
        f"## Thumbnail text\n\n{data['thumbnail_text']}\n"
    )


# --- Thumbnail (deterministic FFmpeg) -----------------------------------------

def _ff_escape_path(path: Path) -> str:
    """Make a Windows path safe inside an FFmpeg filtergraph.

    Forward slashes, and the drive colon escaped as ``\\:`` — two backslashes, because
    the colon is unescaped twice: once by the filtergraph parser, once by drawtext's
    option parser. A single backslash is stripped by the first pass and the bare ':'
    then splits the option (verified on this machine's FFmpeg).
    """
    return str(path).replace("\\", "/").replace(":", r"\\:")


def make_thumbnail(video: Path, text: str, config: dict) -> Path:
    """Grab a still from the video and burn the LLM's text onto it. Returns the PNG path."""
    thumb = config.get("thumbnail", {})
    out = video.with_name(f"{video.stem}_thumb.png")

    fraction = max(0.0, min(0.99, float(thumb.get("frame_at", 0.5))))
    timestamp = fraction * probe_duration(video)

    font = _ff_escape_path(Path(str(thumb.get("font", "C:/Windows/Fonts/impact.ttf"))))
    font_size = int(thumb.get("font_size", 120))
    font_color = str(thumb.get("font_color", "#FFE000"))   # YouTube-gaming yellow

    # Gaming-thumbnail style: Impact font, bright yellow, very thick black stroke.
    # No box, no shadow — the thick border alone gives full readability on any background.
    tmp = tempfile.NamedTemporaryFile(
        "w", suffix=".txt", dir=str(out.parent), delete=False, encoding="utf-8"
    )
    try:
        tmp.write(text)
        tmp.close()
        tf = _ff_escape_path(Path(tmp.name))
        filtergraph = (
            "scale=1280:720,"
            f"drawtext=fontfile={font}:textfile={tf}:expansion=none:"
            f"fontsize={font_size}:fontcolor={font_color}:"
            "borderw=16:bordercolor=black:"
            "x=(w-text_w)/2:y=h-text_h-20"
        )
        run([
            "-ss", f"{timestamp:.3f}", "-i", str(video),
            "-frames:v", "1", "-vf", filtergraph, "-update", "1",
            str(out),
        ])
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    return out


# --- Orchestration ------------------------------------------------------------

def generate_metadata(video_arg: str, preset: str | None = None) -> tuple[Path, Path]:
    """Write metadata (.md + .json) and a thumbnail for one video. Returns (md, thumb).

    `preset` lets the batch pass through the clip's original preset; when omitted we
    detect it from the video's folder (which is usually 'output/' → no preset).
    """
    config = load_config()
    video = _resolve(video_arg, ROOT / config["paths"]["output_dir"])
    if preset is None:
        preset = detect_preset(video, config)
    duration = probe_duration(video)

    print(f"Writing metadata for {video.name}  (preset={preset or 'general'}, "
          f"model={config['llm']['model']})")
    data = call_claude(config, build_llm_prompt(video.name, preset, duration), METADATA_SCHEMA)

    md_path = video.with_name(f"{video.stem}_metadata.md")
    md_path.write_text(render_metadata_md(video.name, data), encoding="utf-8")
    json_path = video.with_name(f"{video.stem}_metadata.json")
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    thumb_path = make_thumbnail(video, data["thumbnail_text"], config)
    return md_path, thumb_path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m editor.meta <video>")
        print("  e.g. python -m editor.meta output/my_game_edited.mp4")
        return 1
    md_path, thumb_path = generate_metadata(sys.argv[1])
    print(f"Wrote {md_path}")
    print(f"Wrote {thumb_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
