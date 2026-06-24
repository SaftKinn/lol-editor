# progress.md — LoL Editor

Living status document. A phase is done only when its **verification gate** is met and the proof
is recorded here.

## Current focus
**Pipeline in daily use. First batch of real clips processed and montage built.**
Filename-instruction system live: clips renamed with trim/mute/group hints are parsed
automatically by the pipeline. First Darius montage (3 clips, Spiel 1) finalised at 1:52.
Next: brand the montage (intro/outro/logo), generate metadata, upload to YouTube.

## Last session (Stage 7 — Upload automation)
- Added `editor/upload.py`: optional stage that uploads a finished clip + `_metadata.json`
  sidecar + `_thumb.png` to YouTube via the Data API. Soft-deps:
  `pip install google-api-python-client google-auth-oauthlib` (same pattern as detect.py).
- OAuth 2.0 flow: browser login once → credentials saved to
  `config/youtube_credentials.json` (gitignored). Auto-refreshes on expiry.
- Short vs long-form detected from filename suffix (`_short`) → picks `youtube_short` or
  `youtube_long` from the `_metadata.json` sidecar. Hashtags injected into description for
  Shorts (with `#Shorts`).
- Resumable upload in 4 MB chunks — network hiccups don't restart from zero.
- Thumbnail set after upload; silently skipped if channel isn't verified for custom thumbnails.
- Optional playlist assignment via `[youtube].default_playlist`.
- Privacy defaults to `"private"` so owner can review clips in YouTube Studio before publishing.
- Wired into `pipeline.py`: `make_upload = false` (default off) in `[batch]`; flips on to
  upload master + Short at end of each clip's processing.
- Added `[youtube]` config section to `config.example.toml` (with step-by-step setup comment).
- Added `config/youtube_client_secrets.json` + `config/youtube_credentials.json` to `.gitignore`.
- Updated CLAUDE.md (Commands + architecture section).
- VERIFY EVIDENCE: ✅ VERIFIED 2026-06-24 — first upload completed successfully.
  Video landed in YouTube Studio (private) on ytriftcarnage@gmail.com. OAuth credentials
  saved to config/youtube_credentials.json; subsequent uploads are silent (no browser).

## Earlier session (Part 2 — detect.py: German keywords + audio preprocessing)
- Diagnosed why `base` Whisper finds 0 segments on all Medal clips:
  1. LoL client was on German → English keywords didn't match.
  2. Stream 0 ("All Audio") includes Discord audio, which competes with the game announcer.
  3. Whisper `base` can't separate the announcer voice from dense LoL game sounds without help.
- Fix applied to `detect.py`:
  - Added German LoL keywords to `_KEYWORDS` (doppelkill, dreifachkill, vierfachkill,
    erster kill, legendär, gottgleich, unaufhaltsam, dominierend, abschuss, baron/drache besiegt).
  - `language` is now configurable (`""` = auto-detect, `"de"` / `"en"` to force).
  - Added optional audio preprocessing (`speech_filter = true`): bandpass 200–4000 Hz +
    `speech_boost = 3.0` volume multiplier. Isolates the announcer frequency range and boosts
    it so Whisper can hear it through the game sound effects.
  - `audio_stream` and `speech_boost` added to `config.example.toml`.
- Confirmed (bandpass test): Discord chat IS in stream 0 ("...at the gym." detected).
  Stream 1 ("All PC Audio") produces 0 segments — different mix. Owner should disable
  Discord in Medal audio settings so stream 0 contains only game audio.
- SCOPE CLARIFICATION: detect.py is designed for FULL-GAME recordings (e.g. OBS, 20–40
  min), NOT for Medal clips. Medal already cuts around the highlight — each Medal clip IS
  the highlight window. For Medal clips, go directly to edit.py → branding → shorts → meta.
  detect.py will be useful when the owner starts recording full games (planned: "full-game
  support" in roadmap). Testing it on Medal clips is the wrong use case.
- Whisper `small` on CUDA fails (cublas64_12.dll missing — CUDA not installed for Python).
- VERIFY EVIDENCE (detect keyword detection): DEFERRED — test when owner has a full-game
  recording. Discord must be off in Medal audio settings for clean game audio.

## Earlier session (Part 2 — Music automation: Freesound integration + highlights extractor)
- Added `editor/music_fetch.py`: fetches royalty-free CC-BY music from Freesound.org API into
  preset pools. Searches by config-driven keywords (`[music_fetch.queries]`), filters by license
  + duration, downloads `preview-hq-mp3` into `music/<preset>/`. Re-runnable (skips existing
  tracks). No new deps — stdlib `urllib` only. Requires free Freesound API key
  (`FREESOUND_API_KEY` env var or `env_file` in config).
- Added `[music_fetch]` section to `config.example.toml`. Default license `"Attribution"` (CC-BY)
  — CC0 pool on Freesound nearly empty; CC-BY fine for monetization with artist credit in description.
  Queries simplified after testing (`"epic gaming"` → 58 results, vs. complex query → 0).
- Added `editor/highlights.py`: reads `_moments.json` from detect.py, cuts one lossless MP4 per
  moment (`-c copy`, keyframe-aligned). Output: `output/<stem>_highlights/` → ready for pipeline.py.
- Fixed Artlist assumption in CLAUDE.md + memory (owner has no Artlist subscription; using
  YouTube Audio Library and/or Freesound instead).
- Published project to GitHub: github.com/SaftKinn/lol-editor (used for Freesound API application).
- VERIFY EVIDENCE (music_fetch): `python -m editor.music_fetch hype` → 5 tracks in `music/hype/`;
  `python -m editor.music_fetch funny` → 4 tracks in `music/funny/`. Key from freesound.org/apiv2/apply/.
- VERIFY EVIDENCE (highlights): import OK; full run requires a real `_moments.json`.

## Earlier session (Part 2 — Content understanding: Whisper announcer detection)
- Added `editor/detect.py`: optional Whisper stage (ADR 0012). Soft-imports `faster-whisper`
  (try/except — pipeline unaffected if not installed). Extracts game audio via FFmpeg (stream 0,
  mono 16 kHz WAV), transcribes with `WhisperModel`, matches against built-in LoL keyword dict
  (first blood, double/triple/quadra/penta kill, ace, legendary, godlike, unstoppable, dominating,
  shutdown, baron/dragon slain, inhibitor). Dedupes near-same-second hits, writes
  `output/<name>_moments.json` with detected time + label + pre-computed window (10s before /
  5s after, configurable). Config: `[detect]` in `config.example.toml` (model, device, windows,
  extra keywords). Stage runs on **raw clips** before edit.py so music hasn't covered the voice.
- Added ADR 0012: Whisper as optional soft dep. Documents alternatives (CLI/API/loudness peaks)
  and why each was rejected; defines `_moments.json` as the interface for a future highlights stage.
- Updated CLAUDE.md Commands + How the code works sections.
- VERIFY EVIDENCE: not yet verified — owner needs `pip install faster-whisper` first.

## Earlier session (Part 2 — Brand assets: name + generator)
- Owner picked the channel name **Rift Carnage** (general LoL highlights, not Darius-only, since
  ARAM is all-random / multi-champ) and the **Hybrid** asset approach (owner sources a real logo,
  code automates intro/outro). Saved as a `channel-name` memory + ADR 0011.
- Added `editor/assets.py` + an `[assets]` config section (channel name, tagline, colors, font,
  durations). `python -m editor.assets` writes `intro.mp4` (2s) + `outro.mp4` (5s) + a placeholder
  `logo.png` into `assets/`. Cards = FFmpeg `color` canvas + stacked `drawtext` (temp `textfile=`)
  + logo overlay + fade in/out, silent video. Re-runnable: the placeholder logo is made ONLY when
  none exists, so a real logo dropped in later is preserved and the cards rebuild around it. Wired
  `[branding]` defaults to `intro.mp4`/`outro.mp4`/`logo.png`.
- **Bug found & fixed during verification (VERIFY EVIDENCE):** the placeholder logo first rendered
  with an opaque black background — proven with `alphaextract,signalstats` (alpha YAVG=255). This
  FFmpeg build ignores the `color` source's `@0.0` alpha and `format=rgba` fills it opaque; fix is
  `colorchannelmixer=aa=0` BEFORE `drawtext` (glyphs keep full alpha → YAVG dropped to ~67).
- Verified end-to-end: regenerated assets, then branded the existing 64s master → **71.0s output**
  (2s intro + 64s main + 5s outro) @ 1280x720, with the red "Rift Carnage" corner logo visible over
  gameplay and **no black box**, HUD/minimap uncropped. Test branded output cleaned up; assets kept.

## Earlier session (Phase 5 — Discovery / first LLM stage)
- Added `editor/meta.py`: stdlib `urllib` Claude client (`call_claude`, structured `output_config`
  JSON), English metadata for two surfaces (youtube_long + youtube_short) + a deterministic FFmpeg
  thumbnail (frame grab at `[thumbnail].frame_at`, scaled 1280x720, LLM `thumbnail_text` burned in
  via `drawtext`). Added `[llm]` (model / key-from-env / optional env_file) and `[thumbnail]` config.
  Wired into `editor/pipeline.py` (`make_metadata`, per clip after Shorts; missing key = skip).
- Decisions (ADR 0010): stdlib over the `anthropic` SDK to honor the zero-dep rule; metadata from
  preset + filename + duration (no transcript/vision yet — that's Part 2); thumbnail = code frame +
  LLM text; key from env var (`ANTHROPIC_API_KEY`), reusable from another project's `.env`.
- Verified end-to-end with the owner's real key (stored in `…\SocialMedia Projekt\.env`) on the
  existing 64s 1280x720 master: on-brand English Darius/ARAM metadata (.md + .json) and a 1280x720
  thumbnail with bold overlay text. One FFmpeg-on-Windows fix: drive colon in `drawtext` paths must
  be escaped as `\\:` (double backslash) — baked into `_ff_escape_path`.
- Owner preference noted: conversation/questions in **German** (code/docs/titles stay English).

## Earlier session (Phase 7 — Batch orchestrator)
- Added `editor/pipeline.py` (`run_batch`, `process_clip`) + a `[batch]` config (`make_shorts`,
  `montage`). It adds no new video logic — it calls `edit` → `brand` → `shorts` per clip and reuses
  `montage.collect_clips` to gather a folder. Branding's "nothing configured" `SystemExit` is caught
  and treated as skip; per-clip failures are isolated so one bad clip won't kill the batch; metadata
  is reported as pending Phase 5. No new ADR — it's orchestration wiring over decided stages.
- Verified: ran on a 2-clip `input/hype/` folder → each clip got a 1280x720 master + a 1080x1920
  Short, music auto-picked by preset, branding skipped, clean summary. Test artifacts cleaned up.

## Earlier session (Phase 6 — Montage)
- Added `editor/montage.py` (`montage`, `collect_clips`, `build_montage_filter`) + a `[montage]`
  config (`music_bed`). Generalized `edit.build_audio_filter` to take filtergraph labels (defaults
  keep Phase 1 bit-identical — verified by string comparison) so the montage reuses the exact
  ducking + −14 LUFS logic for its bed. Reused `presets.choose_music` to pick the bed by preset.
- Chose **one continuous music bed** over keeping per-clip audio (ADR 0009) for "consistent audio";
  `music_bed = false` keeps clip audio. Hard cuts for now (xfade transitions deferred).
- Verified: 3 stress segments (720p + 1080p + silent) from `input/hype/` → 15.07s @ 1280x720, all
  concatenated and normalized; audio in the silent clip's window measured −13.4 dB mean (bed plays
  through). Test artifacts cleaned up.

## Earlier session (Phase 4 — Shorts)
- Added `editor/shorts.py` (`shorts`, `build_shorts_filter`) + a `[shorts]` config section
  (resolution, blur sigma). Implements ADR 0005's blurred-background fit via `split` → blurred
  cover-background + full-width foreground `overlay`. No new ADR — it's a direct implementation of an
  existing decision.
- Verified end-to-end: ran on the Phase 1 edited clip → 1080x1920, 64s, audio copied untouched; an
  extracted frame confirmed the whole game frame centered with HUD + minimap fully visible and a
  blurred top/bottom. Test output cleaned up.

## Earlier session (Phase 3 — branding)
- Added `editor/branding.py` (`brand`, `build_branding_filter`) + ffprobe helpers in `ffmpeg.py`
  (`probe_video`, `has_audio`, shared `_ffprobe`). Renamed config `[intro_outro]` → `[branding]` and
  added logo settings (corner / margin / width / opacity).
- Chose the **concat filter over the stream-copy demuxer** (ADR 0008): robust to arbitrary
  intro/outro (any resolution/fps/codec, even silent); target canvas = the main clip's own size/fps
  so gameplay look is preserved; silent clips get `anullsrc` injected so concat stays aligned.
- Verified end-to-end: branded the Phase 1 clip with a 1920x1080@60 intro + an 854x480@30 silent
  outro + a logo → 68.04s output (intro+main+outro all present), continuous 48 kHz audio, logo
  visible top-right over both intro and gameplay (frames inspected). Test assets/config cleaned up.
- Noted the **Medal ingest path** (`C:\Medal\Clips\League of Legends\`) in memory — the upstream
  source clips are pulled from into the preset folders.

## Earlier session (Phase 2 — presets + music pools)
- Added `editor/presets.py`: `detect_preset` (parent folder → preset), `choose_music` (route to the
  matching pool, deterministic md5-of-clip-name pick, graceful fallback to `music/` root for
  no-preset / empty pool). Made `editor.edit`'s music arg optional; usage now documents the
  auto-by-preset form. Added a `[presets] names = [...]` section to `config.example.toml` and created
  `input/hype|funny/` + `music/hype|funny/` with `.gitkeep`.
- Chose **deterministic per-clip selection** over random/alphabetical/round-robin (ADR 0007): same
  clip → same track (re-runnable), different clips spread across the pool. Used `hashlib.md5`, not
  the built-in `hash()` (salted per process, would break reproducibility).
- Verified: routing + determinism + spread + fallback all PASS; real Medal clip in `input/hype/`
  auto-picked the hype track and rendered a valid 48 kHz output (video copied losslessly).

## Earlier session (project bootstrap + Phase 1)
- Defined the project through an interview with the owner: a monetization-focused, English-facing,
  music-first LoL highlights channel (Darius main + ARAM chaos); mixed hype/funny presets; high
  volume (daily Shorts) → batch automation; Shorts as growth funnel, long-form for revenue.
- Built `editor/` skeleton: `ffmpeg.py`, `config.py`, `edit.py`; `config/config.example.toml`;
  README. Verified the core edit on a real 64s Medal clip + an Artlist track (video copied,
  music ducked, 48 kHz / −14 LUFS output). Fixed a loudnorm sample-rate quirk (forced 48 kHz).
- Wrote the doc set (this file, CLAUDE.md, architecture.md, roadmap.md, ADRs 0001–0006).

## Next concrete step
1. **Brand + upload the montage**: `python -m editor.branding output/montage_final.mp4`
   then `python -m editor.meta output/montage_final_branded.mp4` then upload.
2. **Review the first uploaded clip** in YouTube Studio — publish manually when happy.
3. **Review metadata quality**: check titles/descriptions from real pipeline runs
   and tune the Claude prompt in `meta.py` if the copy isn't on-brand enough.
3. **detect.py + highlights.py (deferred)**: test with a full-game OBS recording
   when the owner starts recording full games.
4. Owner's Hybrid half: drop real `logo.png` into `assets/` and re-run
   `python -m editor.assets` to rebuild intro/outro around it.
Also worth: confirm metadata feel on a real batch in `input/hype/` (Phase 5 verified on a
single master only so far).

## Open questions
- **Channel name / brand** — DECIDED: **Rift Carnage** (ADR 0011). Intro/outro + a placeholder logo
  are generated by `editor/assets.py`; branding now runs end-to-end. Remaining: owner supplies a
  real `logo.png` (Hybrid), and optionally a royalty-free audio sting for the silent intro/outro.
- **Preset assignment** — implemented by input sub-folder (`input/hype/`, `input/funny/`); within a
  pool, tracks are chosen deterministically per clip (ADR 0007). Confirm the feel in real batch use.
- **AI content-understanding scope** — when to add it and how much (cost vs. value at daily
  volume). Whisper announcer-detection is the cheap first step (Part 2 / ADR 0006).
- **Encoder** — NVENC (fast, for volume) vs libx264 (quality/size) for the re-encode stages
  (Shorts/montage/overlays). Default likely NVENC; confirm quality on real output.
- **Full-game recording** — owner *can* record full games for long-form; decide if/when to lean
  into that vs. staying Medal-clip-only.
- **Thumbnails** — owner didn't pick them as a per-video branding element but the goal is
  monetization; Phase 5 builds them anyway (CTR matters) — confirm the style.
- **Medal dual audio tracks** — Medal clips carry two audio streams (game vs PC audio); v1 uses
  the first. Revisit if mic/voice separation is ever needed.

## Decision log
- **ADR 0001** — Local-first, FFmpeg, config-driven, file-based re-runnable stages.
- **ADR 0002** — One source clip, many outputs (16:9 master + 9:16 Shorts + montage).
- **ADR 0003** — English-facing channel, music-first; commentary later.
- **ADR 0004** — Royalty-free music only, organized into preset pools (hype/funny).
- **ADR 0005** — Shorts via blurred-background fit (preserve LoL HUD/minimap).
- **ADR 0006** — Folder-based presets now; AI content-understanding as a later enhancement.
- **ADR 0007** — Deterministic per-clip track selection (md5-of-name) within a pool; re-runnable.
- **ADR 0008** — Branding via the concat filter + overlay (re-encode, normalize inputs), not copy.
- **ADR 0009** — Montage lays one ducked music bed (picked by preset) for consistent audio.
- **ADR 0010** — Discovery via stdlib `urllib` LLM client; preset-driven metadata (no transcript
  yet); thumbnail = deterministic FFmpeg frame + LLM overlay text.
- **ADR 0011** — Channel name "Rift Carnage"; Hybrid brand assets (owner sources real logo, code
  generates intro/outro cards around it via `editor/assets.py`).
- **ADR 0012** — Whisper (`faster-whisper`) as optional soft dep for detect.py; raw-clip audio
  extraction; `_moments.json` sidecar as interface for a future highlights stage.

### Phase → ADR map
- Phase 0–1 (setup / core edit): ADR 0001
- Phase 2 (presets / music): ADR 0004, 0006, 0007
- Phase 3 (branding): ADR 0002, 0008
- Phase 4 (Shorts): ADR 0002, 0005
- Phase 5 (discovery): ADR 0001, 0003, 0010
- Phase 6–7 (montage / batch): ADR 0002, 0009
- Part 2 (brand assets): ADR 0011
- Part 2 (full-game / AI understanding): ADR 0006
