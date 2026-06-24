# CLAUDE.md

Instructions for any AI assistant (Claude) working in this repository. Read first, every session.

## What this project is

**LoL Editor** (working codename — no brand name yet): a local, code-driven video editor that
turns raw League of Legends clips into finished, upload-ready videos for a **monetization-focused**
YouTube channel — single highlight edits, vertical Shorts, and longer montages — all scored with
royalty-free music and consistently branded (intro/outro + logo).

The owner is a **Darius main** who also captures a lot of **ARAM chaos**. Content angle: highlights
/ montages (hype), funny moments, with a Darius + ARAM identity. The channel is **English-facing**
(titles, overlays, metadata in English), **music-first** for now, with English commentary planned
as a later layer. Goal: growth + monetization. Strategy: **Shorts are the growth funnel; long-form
earns** (Shorts RPM is tiny, long-form CPM is where the money is).

Everything heavy runs **locally** via FFmpeg on the owner's PC. The only paid/cloud part is the
LLM that writes metadata (titles/tags/description) and, later, may help classify clips.

> The owner is a beginner programmer. Favor clear, small steps; explain non-obvious choices;
> prefer simple, readable code over clever code.

## Session ritual

State lives on disk so nothing is lost between sessions.

**At the start of every session, read in this order:**
1. This file (`CLAUDE.md`) — conventions
2. `progress.md` — where we are, what's next
3. The highest-numbered file in `docs/decisions/` — the most recent decision

Then say, in 2–3 sentences: where we are and what we're about to do. Don't change files until
that handshake is done.

**At the end of every working session (do this even if not asked):**
1. Update `progress.md` (`## Current focus`, `## Last session`, `## Next concrete step`,
   `## Open questions`, and the `VERIFY EVIDENCE` line of a phase when its gate is met).
2. On a real decision (a trade-off with alternatives weighed), create the next-numbered ADR in
   `docs/decisions/`.

Trigger words from the owner: `wrap up` or `update progress` = do the end-of-session step now.

## Conventions

- **Languages:** code + docs in **English**. Audience-facing text (titles, captions, overlays,
  thumbnails) is **English** (the channel targets the global market — ADR 0003).
- **Config-driven, never hardcoded.** Paths, music pools, resolution, fps, encoder, preset
  settings all live in a config file. Never hardcode a path.
- **Royalty-free music only.** Use Artlist (the owner's subscription) or the YouTube Audio
  Library. Never commit media files (videos/music) to git — only the code.
- **Separate deterministic work from the LLM.** Cutting, audio mixing, encoding, reframing,
  burning overlays, FFmpeg and file handling = code. Creative text (titles, tags, descriptions,
  thumbnail text) and later content classification = LLM. The LLM never sets timings or does math.
- **File-based, re-runnable stages.** Each stage reads files from a folder and writes files back.
  Any stage can be re-run alone.
- **Local-first.** FFmpeg must be on PATH. Use the GPU encoder (NVENC) for re-encodes at volume.
- **Small commits, one idea each** (once git is set up).

## Commands

Python 3.12+ (uses `tomllib`). FFmpeg + ffprobe must be on PATH. No third-party
dependencies, no virtualenv required, no build step — run modules directly from the repo root.

```
# Run the core edit (Stage 1): balance one gameplay clip against one music track.
# Args accept a real path OR a bare name resolved inside the input/ and music/ folders.
python -m editor.edit input/my_game.mp4 music/my_track.mp3
python -m editor.edit my_game.mp4 my_track.mp3      # same thing, bare names

# Auto music by preset (Stage 2): omit the music arg; the track is picked from the
# pool matching the clip's input sub-folder (input/hype/ -> music/hype/).
python -m editor.edit input/hype/my_game.mp4

# Branding (Stage 2 cont.): intro + outro + corner logo onto an edited video.
# Reads intro/outro/logo from [branding] in config; assets live in assets/.
python -m editor.branding output/my_game_edited.mp4

# Shorts (Stage 3): reframe any 16:9 edit to a 9:16 Short (blurred-background fit).
python -m editor.shorts output/my_game_edited.mp4

# Montage (Stage 4): stitch a folder (or a list) of clips into one long-form video.
python -m editor.montage input/hype/

# Batch (Stage 6): run every clip in a folder through edit -> (brand) -> Shorts.
python -m editor.pipeline input/hype/

# Sanity-check the toolchain / config
ffmpeg -version
python -c "from editor.config import load_config; print(load_config())"
```

There is **no test suite, linter, or formatter** configured yet. "Verification" in this project
is manual and evidence-based: run a stage on a real clip, confirm the output plays correctly, and
record the proof in `progress.md` under that phase's `VERIFY EVIDENCE:` line (see `roadmap.md`).
If you add automated tests later, document the command here.

## How the code works (code-level architecture)

`editor/` is a plain Python package run with `python -m editor.<module>`. Eight modules exist today
(only the Stage 5 metadata/LLM stage is missing); each is one stage and is meant to run standalone.

- **`editor/config.py`** — `ROOT` is computed as the folder above `editor/`, so every path is
  resolved relative to the repo regardless of the current working directory. `load_config()` reads
  `config/config.toml`, **falling back to `config/config.example.toml`** if the real one is absent
  (the example holds sane defaults, so the tool runs out-of-the-box). Returns a plain nested dict.
- **`editor/ffmpeg.py`** — the *only* place that shells out. `run(args)` prepends
  `ffmpeg -hide_banner -y` and `check=True`s (raises on non-zero). The probe helpers wrap ffprobe
  JSON: `probe_duration`, `probe_video` (width/height/fps), `has_audio`. Keep all ffmpeg/ffprobe
  invocation behind these helpers.
- **`editor/presets.py`** — Stage 2. `detect_preset(video, config)` reads the clip's parent folder
  name and returns it if it's a configured preset (`config[presets][names]`), else `None`.
  `choose_music(video, config)` routes to `music/<preset>/` (or the `music/` root when there's no
  preset), then maps the clip to one track via a **stable md5-of-clip-name hash** into the sorted
  pool — deterministic per clip (re-runnable, ADR 0007), spread across clips. Built-in `hash()` is
  avoided on purpose (salted per process → not stable). Empty pool falls back to `music/` root.
- **`editor/edit.py`** — Stage 1, the pattern every future stage should follow:
  - `_resolve(given, default_dir)` lets a CLI arg be either a real path or a bare filename living
    in the stage's default folder — reuse this for new stages.
  - The work is expressed as an **FFmpeg `filter_complex` graph built as a string**
    (`build_audio_filter`), not via a Python media library. Audio is resampled to 48 kHz, music is
    `volume`-scaled, optionally **ducked** under game audio via `sidechaincompress` (the gameplay is
    `asplit`'d into a mix copy + a sidechain key), the two are `amix`'d, then `loudnorm`'d to the
    target LUFS. The `loudnorm` filter can emit an odd sample rate, so a trailing `aresample=48000`
    forces it back — keep that when copying the pattern.
  - **Copy-vs-re-encode is the key branch:** if `config[video].resolution`/`fps` are empty, the
    video stream is `-c:v copy`'d untouched (lossless, fast — only audio is rebuilt). Setting either
    triggers a `scale`/`fps` filter and an `libx264` re-encode. The output is always
    `output/<video-stem>_edited.mp4` with `+faststart` and `-shortest`.

- **`editor/branding.py`** — Stage 2 branding. Joins `intro + main + outro` with the FFmpeg
  **concat filter** (each clip normalized: scale+pad to a common canvas, fixed fps, 48 kHz stereo)
  rather than the stream-copy demuxer, so arbitrary intro/outro just work (ADR 0008). A clip with no
  audio gets `anullsrc` silence injected so concat stays aligned. The logo is `overlay`'d over the
  whole result, positioned by a config corner+margin. Always re-encodes. Target canvas defaults to
  the **main clip's** own size/fps so the gameplay look is preserved. All of intro/outro/logo are
  optional via `[branding]`; the stage errors only if all three are unset.

- **`editor/shorts.py`** — Stage 3. Reframes 16:9 → 9:16 with a blurred-background fit (ADR 0005):
  `split` the frame, scale one copy to **cover** the target and blur it (background), scale the other
  to the full target **width** (foreground, nothing cropped — HUD/minimap survive), `overlay` the
  foreground centered. Video re-encodes (libx264); audio is `-c:a copy` (the mix is unchanged).
  Target size + blur sigma come from `[shorts]`. Output `<name>_short.mp4`.
- **`editor/montage.py`** — Stage 4. Stitches several clips (or a whole preset folder) into one
  long-form video with the concat filter (same normalize-each pattern as branding). By default lays
  ONE ducked music bed under the whole montage for consistent audio (ADR 0009): it reuses
  `presets.choose_music` to pick the bed by preset and **`edit.build_audio_filter`** for the exact
  ducking + −14 LUFS — that function takes optional graph-label args so the montage feeds it the
  concatenated game audio `[cg]` + the looped music input. `[montage].music_bed = false` keeps each
  clip's own audio. Silent clips get `anullsrc` injected so the bed plays through.

- **`editor/pipeline.py`** — Stage 6 batch orchestrator. Adds no video logic: it imports and calls
  `edit` → `brand` → `shorts` per clip and reuses `montage.collect_clips` to gather a folder.
  Branding's "nothing configured" `SystemExit` is caught = skip; per-clip failures are isolated so
  one bad clip doesn't kill the batch; metadata is reported as pending Stage 5. `[batch]` toggles
  `make_shorts` and an optional end-of-run `montage`.

Note the reuse seam: `edit.build_audio_filter(..., game, music, out)` is the single place audio
ducking/loudness lives — call it with labels rather than reimplementing the mix in a new stage. The
batch (`pipeline.py`) is the other seam: new per-clip stages should slot into `process_clip` rather
than grow their own folder-walking loop.

New stages should: load config, resolve inputs with `_resolve`, build a filtergraph string, run it
through `ffmpeg.run`, write to `output/`, and expose a `main()` so `python -m editor.<stage>` works.

## The pipeline (one line)

Raw clip(s) → (optional highlight detection) → balance game audio + music (ducked) → brand
(intro/outro + logo) → render 16:9 master + cut 9:16 Shorts (blurred-bg fit) + stitch montages →
thumbnail + English metadata → owner uploads.

Full detail in `architecture.md`. The plan and phases are in `roadmap.md`.
