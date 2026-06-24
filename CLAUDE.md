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
- **Royalty-free music only.** Use the **YouTube Audio Library** (free, safe for monetized
  YouTube) or **Pixabay Music** (CC0, no attribution required). No Artlist subscription.
  Never commit media files (videos/music) to git — only the code.
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
`editor/detect.py` is the one exception: it needs `pip install faster-whisper` (optional; the
rest of the pipeline works without it).

```
# Run the core edit (Stage 1): balance one gameplay clip against one music track.
# Args accept a real path OR a bare name resolved inside the input/ and music/ folders.
python -m editor.edit input/my_game.mp4 music/my_track.mp3
python -m editor.edit my_game.mp4 my_track.mp3      # same thing, bare names

# Auto music by preset (Stage 2): omit the music arg; the track is picked from the
# pool matching the clip's input sub-folder (input/hype/ -> music/hype/).
python -m editor.edit input/hype/my_game.mp4

# Brand assets (Part 2): generate intro.mp4 + outro.mp4 + a placeholder logo.png into
# assets/ from [assets] in config (channel name, colors, font). Re-runnable: it only
# makes the placeholder logo when none exists, so dropping in a real logo.png and
# re-running rebuilds the intro/outro AROUND your logo (the "Hybrid" path, ADR 0011).
python -m editor.assets

# Branding (Stage 2 cont.): intro + outro + corner logo onto an edited video.
# Reads intro/outro/logo from [branding] in config; assets live in assets/.
python -m editor.branding output/my_game_edited.mp4

# Shorts (Stage 3): reframe any 16:9 edit to a 9:16 Short (blurred-background fit).
python -m editor.shorts output/my_game_edited.mp4

# Montage (Stage 4): stitch a folder (or a list) of clips into one long-form video.
python -m editor.montage input/hype/

# Metadata + thumbnail (Stage 5, the only LLM stage): English title/tags/description
# + a thumbnail (frame grab + bold overlay text) for one finished video.
# Needs a Claude API key — set ANTHROPIC_API_KEY (or [llm].env_file in config).
python -m editor.meta output/my_game_edited.mp4

# Batch (Stage 6): run every clip in a folder through edit -> (brand) -> Shorts -> metadata.
python -m editor.pipeline input/hype/

# Highlight detection (Part 2, optional): find LoL announcer moments (Pentakill, Ace, …)
# in a raw clip by transcribing with Whisper. Run BEFORE edit.py (game audio is cleanest).
# Writes output/<name>_moments.json. Needs: pip install faster-whisper (one-time).
python -m editor.detect input/my_game.mp4

# Highlight extraction (Part 2): cut one short MP4 per detected moment from a raw clip.
# Input: sidecar JSON from detect.py, a video path, or a bare clip name.
# Output: output/<stem>_highlights/00_pentakill.mp4, 01_ace.mp4, …
# Clips drop straight into edit.py or pipeline.py for scoring + branding.
python -m editor.highlights output/my_game_moments.json
python -m editor.highlights input/my_game.mp4   # finds sidecar automatically

# Sanity-check the toolchain / config
ffmpeg -version
python -c "from editor.config import load_config; print(load_config())"
```

There is **no test suite, linter, or formatter** configured yet. "Verification" in this project
is manual and evidence-based: run a stage on a real clip, confirm the output plays correctly, and
record the proof in `progress.md` under that phase's `VERIFY EVIDENCE:` line (see `roadmap.md`).
If you add automated tests later, document the command here.

## How the code works (code-level architecture)

`editor/` is a plain Python package run with `python -m editor.<module>`. All stage modules now
exist (the deterministic FFmpeg stages plus the one LLM stage, `meta.py`); each is one stage and is
meant to run standalone.

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

- **`editor/assets.py`** — Part 2 brand-asset generator (the code half of the "Hybrid"
  decision, ADR 0011). `python -m editor.assets` writes `intro.mp4`, `outro.mp4` and a
  placeholder `logo.png` into `assets/` from `[assets]` config (channel name, tagline,
  colors, font, durations). Cards are built like the `meta.py` thumbnail — an FFmpeg `color`
  canvas + stacked `drawtext` (text via temp `textfile=` to dodge escaping) + the logo
  overlaid on top + fade in/out. Both cards are **silent** video on purpose (branding injects
  matching silence on concat). Re-runnable & safe: the placeholder logo is generated **only
  when no `logo.png` exists**, so a real logo dropped in later is never overwritten and the
  cards rebuild around it. **Transparency gotcha:** this FFmpeg build ignores the `black@0.0`
  alpha suffix on the `color` source and `format=rgba` fills alpha opaque, so the placeholder
  logo forces a transparent background with `colorchannelmixer=aa=0` *before* `drawtext`
  (glyphs get full alpha back) — without it the corner logo is an opaque black box over
  gameplay. Reuses `meta._ff_escape_path` for the Windows drive-colon escaping.
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

- **`editor/meta.py`** — Stage 5, the **only LLM stage** and the only cloud/paid part (ADR 0001,
  0010). Calls the Claude API directly over HTTPS with the **standard library** (`urllib`, no SDK —
  keeps the project dependency-free) using structured outputs (`output_config.format` + a JSON
  schema) so the reply is guaranteed-valid JSON. Model + key are config-driven (`[llm]`: `model`
  default `claude-sonnet-4-6`; key read from env var `api_key_env`, with an optional `env_file`
  escape hatch). It has no transcript/vision, so it writes preset-driven English metadata
  (youtube_long + youtube_short) from the clip's preset + name + duration. The **thumbnail keeps the
  deterministic/creative split**: code grabs a still at `[thumbnail].frame_at` (scaled 1280x720) and
  burns the LLM's short `thumbnail_text` on with `drawtext`; the LLM only writes the wording. Outputs
  flat siblings: `<name>_metadata.md`, `<name>_metadata.json`, `<name>_thumb.png`. Gotcha baked into
  `_ff_escape_path`: the Windows drive colon must be `\\:` (double backslash) for `drawtext`.
- **`editor/detect.py`** — Part 2 optional stage (ADR 0012). Soft-imports `faster-whisper`
  (try/except so the core pipeline never breaks if it's absent). Extracts the first audio stream
  via FFmpeg as a mono 16 kHz WAV (the format Whisper expects), transcribes with `WhisperModel`,
  and matches each segment's text against a built-in dict of LoL announcer keywords. Near-same-
  second duplicates are deduped. Writes `output/<name>_moments.json` — a list of
  `{time, label, window_start, window_end}` objects — as a cut-list sidecar for
  `editor/highlights.py`. Config: `[detect]` (model size, device cpu/cuda, window widths, extra
  keywords). **Run on raw clips before `edit.py`** — the game audio is cleanest before music is
  added. Medal clips have two audio tracks; stream 0 (game audio) is extracted by default.

- **`editor/highlights.py`** — Part 2 stage. Reads a `_moments.json` sidecar from `detect.py`
  and cuts one short MP4 per detected moment using FFmpeg `-c copy` (no re-encode — fast and
  lossless, keyframe-aligned). Input accepts the sidecar path directly, a video path, or a bare
  clip name (sidecar is located automatically in `output/`). Locates the source clip anywhere
  under `input/` (including preset sub-folders). Output goes to
  `output/<stem>_highlights/00_pentakill.mp4`, `01_ace.mp4`, … Resulting clips are ready input
  for `edit.py` (single clip) or `pipeline.py` (whole folder batch).

- **`editor/pipeline.py`** — Stage 6 batch orchestrator. Adds no video logic: it imports and calls
  `edit` → `brand` → `shorts` → `meta` per clip and reuses `montage.collect_clips` to gather a folder.
  Branding's "nothing configured" `SystemExit` is caught = skip; a missing API key makes `meta`
  `SystemExit` = skip too; per-clip failures are isolated so one bad clip doesn't kill the batch.
  `[batch]` toggles `make_shorts`, `make_metadata`, and an optional end-of-run `montage`.

Note the reuse seam: `edit.build_audio_filter(..., game, music, out)` is the single place audio
ducking/loudness lives — call it with labels rather than reimplementing the mix in a new stage. The
batch (`pipeline.py`) is the other seam: new per-clip stages should slot into `process_clip` rather
than grow their own folder-walking loop.

New stages should: load config, resolve inputs with `_resolve`, build a filtergraph string, run it
through `ffmpeg.run`, write to `output/`, and expose a `main()` so `python -m editor.<stage>` works.
(The LLM stage `meta.py` is the exception that proves the rule: deterministic FFmpeg + config +
`_resolve` + `main()`, but its creative text comes from `call_claude` instead of a filtergraph.)

## The pipeline (one line)

Raw clip(s) → (optional highlight detection) → balance game audio + music (ducked) → brand
(intro/outro + logo) → render 16:9 master + cut 9:16 Shorts (blurred-bg fit) + stitch montages →
thumbnail + English metadata → owner uploads.

Full detail in `architecture.md`. The plan and phases are in `roadmap.md`.
