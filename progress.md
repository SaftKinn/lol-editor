# progress.md — LoL Editor

Living status document. A phase is done only when its **verification gate** is met and the proof
is recorded here.

## Current focus
**Phase 7 — Batch orchestrator complete and verified.** `editor/pipeline.py` chains the existing
stages per clip over a whole preset folder: edit → (branding, auto-skipped when no assets) → Shorts,
with an optional batch montage. Reuses `montage.collect_clips`. Verified on a 2-clip folder (master +
Short each, one command). **Only Phase 5 (discovery/LLM) remains** — blocked on the owner's LLM API
key. The deterministic FFmpeg pipeline (Phases 0–4, 6, 7) is now end-to-end.

## Last session (Phase 7 — Batch orchestrator)
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
Build **Phase 5 (discovery)** — the only remaining stage and the first LLM one: generate an English
title + tags + description per video and a thumbnail (a frame + bold text). Introduces the
config-driven LLM model + key (ADR 0001 keeps the LLM separate from the deterministic FFmpeg work).
**Needs the owner to provide an LLM API key + provider/model choice** before it can be verified
end-to-end (like Phase 3 needs real assets). Once built, fold it into `pipeline.py` so the batch
emits metadata per clip too. The thumbnail's frame extraction is deterministic (FFmpeg); only the
text/title is the LLM's job.

## Open questions
- **Channel name / brand** — none yet; using working codename **LoL Editor**. Needed before
  designing intro/outro/logo. **Now the one blocker on Phase 3 real use:** `editor/branding.py` is
  built and verified, but needs real `assets/intro.mp4` / `outro.mp4` / `logo.png`.
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

### Phase → ADR map
- Phase 0–1 (setup / core edit): ADR 0001
- Phase 2 (presets / music): ADR 0004, 0006, 0007
- Phase 3 (branding): ADR 0002, 0008
- Phase 4 (Shorts): ADR 0002, 0005
- Phase 5 (discovery): ADR 0003
- Phase 6–7 (montage / batch): ADR 0002, 0009
- Part 2 (full-game / AI understanding): ADR 0006
