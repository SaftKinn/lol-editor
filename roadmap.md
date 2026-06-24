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
`VERIFY EVIDENCE:` MET (2026-06-24) — `editor/presets.py` added; `editor.edit` now takes music
optionally and auto-picks by preset. Verified: `detect_preset` maps `input/<preset>/` → preset and
unknown/no sub-folder → None; `choose_music` routes a hype clip to `music/hype/` and a funny clip to
`music/funny/`, is deterministic per clip (same clip → same track on re-run) and spreads 20 clips
across a 2-track pool; empty pool / no-preset falls back to `music/` root. Real end-to-end render of
a Medal clip in `input/hype/` auto-picked the `music/hype/` track and produced a valid 48 kHz output
(video copied losslessly).

### Phase 3 — Branding (intro/outro + logo)
**Goal:** every video is recognizably the channel's.
- Prepend intro, append outro, overlay a corner logo/watermark throughout.
**Verify:** output has the intro, outro, and a visible logo; audio stays in sync.
`VERIFY EVIDENCE:` MET (2026-06-24) — `editor/branding.py` added (concat filter + overlay, ADR
0008). Verified end-to-end on the Phase 1 edited clip with synthetic assets chosen to stress the
pipeline: a 1920x1080@60 intro and an 854x480@30 **silent** outro. Output: 68.04s (= 2s intro + 64s
main + 2s outro, so both are present), one continuous 48 kHz audio track (silence auto-injected for
the silent outro), normalized to the main clip's 1280x720@60. Extracted frames confirmed the yellow
logo overlaid top-right over both the intro and the gameplay. Real channel assets are still pending
(brand undecided), but the mechanism is proven.

### Phase 4 — Shorts (9:16)
**Goal:** a vertical Short from any edit.
- Reframe to 9:16 with a **blurred-background fit** (full frame visible, edges never cropped).
**Verify:** a 9:16 clip where the HUD/minimap are fully visible and the video is upload-ready.
`VERIFY EVIDENCE:` MET (2026-06-24) — `editor/shorts.py` added (split → blurred-cover background +
full-width foreground overlay, ADR 0005). Ran on the Phase 1 edited clip: output is 1080x1920, 64s,
audio copied untouched. An extracted frame confirmed the full game frame centered with the HUD/
ability bar and minimap fully visible (nothing cropped), top/bottom filled with a blurred copy.

### Phase 5 — Discovery (title / tags / description / thumbnail)
**Goal:** the parts that drive click-through and reach (the monetization goal).
- LLM writes an English title + tags + description per video; a thumbnail from a frame + text.
**Verify:** for one clip, `output/<name>/` has the video plus English metadata + a thumbnail.
`VERIFY EVIDENCE:` MET (2026-06-24) — `editor/meta.py` added (stdlib `urllib` Claude client,
structured-output JSON, ADR 0010). Ran on a real 64s 1280x720 master with `claude-sonnet-4-6`:
wrote `_metadata.md` + `_metadata.json` (on-brand English Darius/ARAM title, 15 tags, Shorts
hashtags) and a 1280x720 `_thumb.png` — a frame grabbed at 50% (landed on a QUADRA KILL) with
the LLM's bold overlay text ("NOBODY WAS SAFE") burned in via drawtext. Wired into
`editor/pipeline.py` (per clip after Shorts; missing API key = skip, not fail).

### Phase 6 — Montage (long-form)
**Goal:** stitch several clips into one longer highlight video (the higher-CPM format).
- Concat selected clips with transitions; single music bed or per-segment.
**Verify:** one montage plays start to finish with consistent audio and branding.
`VERIFY EVIDENCE:` MET (2026-06-24) — `editor/montage.py` added (concat filter + one ducked music
bed picked by preset, ADR 0009). Stitched 3 stress-test segments (720p + a 1080p + a **silent** one)
from `input/hype/`: output 15.07s @ 1280x720 (all three concatenated, the 1080p clip normalized in),
one bed picked via preset fallback. Audio in the silent clip's window (11–14s) measured mean −13.4 dB
(not silence) — the bed plays continuously across every cut, so the audio is consistent end to end.

### Phase 7 — Batch orchestrator ⭐
**Goal:** the daily-volume engine.
- Drop many clips in `input/<preset>/`, run one command → master + Short + metadata for each.
**Verify:** a folder of clips produces a full set of outputs without per-clip handwork.
`VERIFY EVIDENCE:` MET (2026-06-24) — `editor/pipeline.py` chains edit → (branding, auto-skipped
with no assets) → Shorts per clip. Ran on a 2-clip `input/hype/` folder in one command: each clip
produced a 1280x720 master (`*_edited.mp4`) + a 1080x1920 Short (`*_short.mp4`), music auto-picked by
preset, branding skipped cleanly, a per-clip summary printed, and metadata reported as pending
(Phase 5). No per-clip handwork. Optional batch montage flag wires to the verified Phase 6 stage.

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
