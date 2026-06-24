# LoL Editor — Rift Carnage

A local, code-driven video editor that turns raw **League of Legends** gameplay clips into
upload-ready videos for a monetization-focused YouTube channel.

**Channel:** [Rift Carnage](https://www.youtube.com/) — LoL highlights, Darius plays, ARAM chaos.
**Outputs:** 16:9 masters for long-form · 9:16 vertical Shorts · highlight montages.

Everything runs locally via **FFmpeg** — no cloud, no subscriptions, no upload until you decide.
The only external services are:
- **Freesound.org** (this project) — to auto-download royalty-free music into the preset pools.
- **Claude API** (Anthropic) — to write English YouTube metadata (titles, tags, descriptions).

---

## How it works

Raw clip → balance audio + music → brand (intro/outro + logo) → 16:9 master + 9:16 Short →
thumbnail + metadata → owner uploads.

Each step is a separate Python module, file-based and re-runnable. Any stage can run alone.

---

## Stages

| Module | What it does |
|---|---|
| `editor/edit.py` | Balance game audio against a music bed (ducked, −14 LUFS) |
| `editor/presets.py` | Route clips to the right music pool (`hype/`, `funny/`) |
| `editor/branding.py` | Prepend intro + append outro + overlay corner logo |
| `editor/shorts.py` | Reframe 16:9 → 9:16 with a blurred-background fit (HUD stays visible) |
| `editor/montage.py` | Stitch several clips into one long-form video with a single music bed |
| `editor/pipeline.py` | Batch: run every clip in a folder through all stages |
| `editor/assets.py` | Generate intro.mp4 / outro.mp4 / logo placeholder from config |
| `editor/meta.py` | Write English YouTube metadata + thumbnail via Claude API (LLM stage) |
| `editor/detect.py` | Find highlight moments (Pentakill, Ace, …) via Whisper transcription |
| `editor/highlights.py` | Cut short clips around each detected moment for the pipeline |
| **`editor/music_fetch.py`** | **Auto-download royalty-free music from Freesound into preset pools** |

---

## Freesound integration (`editor/music_fetch.py`)

The pipeline organizes music into **preset pools** — one folder per content type:

```
music/
  hype/    ←  epic / aggressive / gaming tracks
  funny/   ←  quirky / playful / comedy tracks
```

`music_fetch.py` fills these pools automatically using the **Freesound API**:

1. Searches by preset-specific keywords (e.g. `"epic aggressive gaming electronic"`)
2. Filters for **CC0 license** (safe for monetized YouTube — no attribution required)
3. Filters by duration (60–360 s — real music, not sound effects)
4. Downloads the high-quality MP3 preview into the matching preset folder
5. Skips tracks already on disk (re-runnable, idempotent)

```bash
python -m editor.music_fetch              # fill all preset pools
python -m editor.music_fetch hype         # fill one pool
```

Search keywords are config-driven — no hardcoded queries:

```toml
[music_fetch.queries]
hype   = "epic aggressive gaming electronic"
funny  = "quirky playful comedy upbeat"
```

Once tracks are downloaded, the pipeline picks them automatically — no further interaction needed.

---

## Setup

**Requirements:** Python 3.12+, FFmpeg on PATH.

```bash
# 1. Copy the config
copy config\config.example.toml config\config.toml

# 2. Set your Freesound API key
set FREESOUND_API_KEY=your_key_here

# 3. Download music for your preset pools
python -m editor.music_fetch

# 4. Drop a raw clip into input/hype/ and run the full pipeline
python -m editor.pipeline input/hype/
```

No virtualenv, no third-party dependencies (the core pipeline is stdlib + FFmpeg only).
`editor/detect.py` is the one exception: `pip install faster-whisper` to enable it.

---

## Commands

```bash
# Core edit: balance one clip against one music track
python -m editor.edit input/my_game.mp4 music/my_track.mp3

# Auto music by preset folder
python -m editor.edit input/hype/my_game.mp4

# Brand (intro + outro + logo)
python -m editor.branding output/my_game_edited.mp4

# Vertical Short (9:16, blurred background)
python -m editor.shorts output/my_game_edited.mp4

# Montage from a folder
python -m editor.montage input/hype/

# Full batch pipeline
python -m editor.pipeline input/hype/

# Generate brand assets (intro.mp4 / outro.mp4 / logo placeholder)
python -m editor.assets

# Write YouTube metadata + thumbnail (needs ANTHROPIC_API_KEY)
python -m editor.meta output/my_game_edited.mp4

# Detect highlight moments via Whisper (needs: pip install faster-whisper)
python -m editor.detect input/my_game.mp4

# Cut highlight clips from detected moments
python -m editor.highlights output/my_game_moments.json

# Download royalty-free music from Freesound (needs FREESOUND_API_KEY)
python -m editor.music_fetch
```

---

## Config

All paths, music settings, and API keys are in `config/config.toml` (copy from
`config/config.example.toml`). Nothing is hardcoded. API keys stay out of git via
environment variables.

---

## License

Code: MIT. Media files (clips, music, renders) are excluded from git entirely — they stay local.
