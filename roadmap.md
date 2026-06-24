# roadmap.md — LoL Editor

Goal: **the smallest version that already produces one upload-ready video** — then grow outward
toward the daily-volume, monetization-focused workflow. Every phase has a **verification gate**:
it is only "done" when the proof exists and is recorded in `progress.md`.

Order follows lowest-risk-first, and roughly the value order for a growth+monetization channel.

---

## Working with Claude (model & effort hints)

- **Mechanical FFmpeg stages** (audio mix, reframe, concat, overlays) → a fast model at medium
  effort is fine.
- **Creative/fiddly stages** (metadata text, thumbnail wording, highlight detection tuning) →
  step the model/effort up.
- The LLM model is config-driven (start cheap with Sonnet; switch to Opus for quality runs).

---

## Part 1 — MVP: a repeatable single-clip → upload-ready video

### Phase 0 — Setup
**Goal:** project skeleton, FFmpeg reachable, config in place.
**Verify:** `ffmpeg -version` works; `editor.config.load_config()` reads the config.
`VERIFY EVIDENCE:` MET (2026-06-24) — skeleton built; FFmpeg v8.1.1 on PATH; config loads.

### Phase 1 — Core edit (audio + music) ⭐
**Goal:** one clip + one royalty-free track → balanced, upload-ready file.
- Keep game audio in front, music underneath (looped), duck music on loud moments, normalize
  to −14 LUFS, copy video untouched unless resize/fps requested.
**Verify:** run on a real clip; output plays, music sits under the gameplay, loudness sane.
`VERIFY EVIDENCE:` MET (2026-06-24) — `editor.edit` on a real 64s Medal clip (720p/60) +
Artlist track: video copied losslessly, music ducked under game audio, output 48 kHz AAC,
−14 LUFS. **First "it works" milestone.**

### Phase 2 — Presets + music pools
**Goal:** "hype" vs "funny" select an editing style + music pool automatically.
- Read the preset from the input sub-folder (`input/hype/`, `input/funny/`); pick a track from
  the matching `music/<preset>/` pool.
**Verify:** the same clip in each preset folder produces edits with the right music pool/style.
`VERIFY EVIDENCE:`

### Phase 3 — Branding (intro/outro + logo)
**Goal:** every video is recognizably the channel's.
- Prepend intro, append outro, overlay a corner logo/watermark throughout.
**Verify:** output has the intro, outro, and a visible logo; audio stays in sync.
`VERIFY EVIDENCE:`

### Phase 4 — Shorts (9:16)
**Goal:** a vertical Short from any edit.
- Reframe to 9:16 with a **blurred-background fit** (full frame visible, edges never cropped).
**Verify:** a 9:16 clip where the HUD/minimap are fully visible and the video is upload-ready.
`VERIFY EVIDENCE:`

### Phase 5 — Discovery (title / tags / description / thumbnail)
**Goal:** the parts that drive click-through and reach (the monetization goal).
- LLM writes an English title + tags + description per video; a thumbnail from a frame + text.
**Verify:** for one clip, `output/<name>/` has the video plus English metadata + a thumbnail.
`VERIFY EVIDENCE:`

### Phase 6 — Montage (long-form)
**Goal:** stitch several clips into one longer highlight video (the higher-CPM format).
- Concat selected clips with transitions; single music bed or per-segment.
**Verify:** one montage plays start to finish with consistent audio and branding.
`VERIFY EVIDENCE:`

### Phase 7 — Batch orchestrator ⭐
**Goal:** the daily-volume engine.
- Drop many clips in `input/<preset>/`, run one command → master + Short + metadata for each.
**Verify:** a folder of clips produces a full set of outputs without per-clip handwork.
`VERIFY EVIDENCE:`

---

## Part 2 — Bigger rocks (later)

- **Full-game support:** record full games; find highlights automatically — primarily via the LoL
  **announcer** (Whisper, reused from ORIGIN: "Pentakill", "Ace", …) for precise timestamps +
  auto-tags; loudness peaks as a fallback.
- **AI content-understanding:** vision LLM on sampled frames to auto-classify hype/funny, pick the
  thumbnail moment, and sharpen titles — used sparingly to control cost at volume.
- **Upload automation:** YouTube API upload/scheduling (own decision; manual upload until then).
- **Channel brand:** pick a name; design intro/outro/logo around it.
- **Later:** English commentary layer for long-form; possibly other games.
