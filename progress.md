# progress.md — LoL Editor

Living status document. A phase is done only when its **verification gate** is met and the proof
is recorded here.

## Current focus
**Phase 1 — Core edit complete and verified.** `editor/edit.py` balances game audio against a
royalty-free music track (ducked, normalized to −14 LUFS) and exports an upload-ready file,
copying the video stream losslessly. Proven on a real Medal clip. The project skeleton, config,
and FFmpeg helpers are in place. Next up: **Phase 2 (presets + music pools)** or **Phase 3
(branding)**.

## Last session (project bootstrap + Phase 1)
- Defined the project through an interview with the owner: a monetization-focused, English-facing,
  music-first LoL highlights channel (Darius main + ARAM chaos); mixed hype/funny presets; high
  volume (daily Shorts) → batch automation; Shorts as growth funnel, long-form for revenue.
- Built `editor/` skeleton: `ffmpeg.py`, `config.py`, `edit.py`; `config/config.example.toml`;
  README. Verified the core edit on a real 64s Medal clip + an Artlist track (video copied,
  music ducked, 48 kHz / −14 LUFS output). Fixed a loudnorm sample-rate quirk (forced 48 kHz).
- Wrote the doc set (this file, CLAUDE.md, architecture.md, roadmap.md, ADRs 0001–0006).

## Next concrete step
Build **Phase 2 (presets + music pools)**: read the preset from the input sub-folder
(`input/hype/`, `input/funny/`) and pick a track from the matching `music/<preset>/` pool, so the
editing style + music follow the clip automatically. (Or Phase 3 branding first — owner's call.)

## Open questions
- **Channel name / brand** — none yet; using working codename **LoL Editor**. Needed before
  designing intro/outro/logo.
- **Preset assignment** — provisionally by input sub-folder (owner said "you recommend"); confirm
  once Phase 2 is in use.
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

### Phase → ADR map
- Phase 0–1 (setup / core edit): ADR 0001
- Phase 2 (presets / music): ADR 0004, 0006
- Phase 3 (branding): ADR 0002
- Phase 4 (Shorts): ADR 0002, 0005
- Phase 5 (discovery): ADR 0003
- Phase 6–7 (montage / batch): ADR 0002
- Part 2 (full-game / AI understanding): ADR 0006
