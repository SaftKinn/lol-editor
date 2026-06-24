# ADR 0011 — Brand assets: channel name "Rift Carnage", Hybrid logo + code-generated cards

- Status: accepted
- Date: 2026-06-24

## Context
Branding (Stage 2, `editor/branding.py`) was built and verified in Phase 3 but had nothing
to run with: there were no real `intro.mp4` / `outro.mp4` / `logo.png`. This was the one
blocker on Phase 3's real use and the strongest first rock of Part 2 (see `progress.md`).
Two things had to be decided: the channel's **name** (a creative, owner-only call) and **how
to produce the three assets**.

The channel is a music-first, English-facing LoL highlights channel. It started as Darius-
focused, but the owner plays many champions (ARAM is all-random), so a Darius-only brand name
would be too narrow.

## Decision
**1. Channel name: "Rift Carnage."** Map-wide ("Rift" = Summoner's Rift, every champ/mode),
alliterative, and carries the hype / Pentakill / montage energy without locking the brand to
one champion. Chosen by the owner over Darius-specific names (DariusDiff, Hand of Noxus) and
other general options (Rift Rampage, Rift Riot, Pentakill Plays).

**2. Asset production: Hybrid.** The owner sources a **real logo** themselves (AI image
generator / Canva / a cheap designer) — the logo is the brand's face, appears in every video,
the avatar and the banner, and is where amateur-vs-pro shows most; FFmpeg can only render text.
**Code generates the repetitive cards** (`intro.mp4` / `outro.mp4`) around that logo, because
they must be consistent and short, which automation does better than hand-editing each time.

**3. A new code-generated stage `editor/assets.py`** implements the code half. It is
config-driven (`[assets]`: channel name, tagline, colors, font, durations) and builds each
card the same way `meta.py` builds the thumbnail: an FFmpeg `color` canvas + stacked
`drawtext` (text via temp `textfile=` to avoid escaping) + the logo overlaid + fade in/out.
Cards are silent video (branding injects matching silence on concat). It is **re-runnable and
safe**: a placeholder `logo.png` is generated only when none exists, so dropping in the real
logo later never overwrites it and rebuilds the cards around it. `[branding]` now defaults
`intro`/`outro`/`logo` to these filenames so branding picks them up automatically.

## Alternatives considered
- **All code-generated (incl. logo):** fastest, fully automated, but the logo would be plain
  text on a fill — generic, and the logo is exactly where polish matters. Rejected as the
  permanent answer; kept only as the *placeholder* so the pipeline runs today.
- **All externally designed (incl. intro/outro):** highest polish everywhere, but makes the
  owner hand-build and re-export the repetitive cards and blocks progress until files arrive.
  Rejected — automation wins on the repetitive, must-be-consistent pieces.
- **A Darius-specific name** (DariusDiff, Hand of Noxus): strong identity but too narrow given
  multi-champ / ARAM content. Rejected by the owner.

## Consequences
- Phase 3 (branding) is now runnable end-to-end: verified by branding the existing 64s master
  → a 71s output (2s intro + 64s main + 5s outro) at 1280x720, with the red "Rift Carnage"
  corner logo visible over gameplay and the HUD/minimap uncropped.
- A reusable FFmpeg transparency gotcha is now documented and handled: this build ignores the
  `color` source's `@0.0` alpha and `format=rgba` fills alpha opaque (proven with
  `alphaextract,signalstats` → YAVG 255). The fix is `colorchannelmixer=aa=0` **before**
  `drawtext`, so only glyph pixels keep full alpha (YAVG dropped to ~67). Without it the corner
  logo renders as an opaque black box over gameplay.
- `assets.py` is a **setup/occasional** stage, not a per-clip pipeline step — it is run when
  branding or the brand identity changes, so it is intentionally not wired into
  `editor/pipeline.py`.
- The placeholder logo is functional but plain; replacing it with a real logo (owner's half of
  the Hybrid) remains an open task before going live. The generated intro/outro are silent —
  a short audio sting could be layered later but needs a royalty-free asset (ADR 0004).
