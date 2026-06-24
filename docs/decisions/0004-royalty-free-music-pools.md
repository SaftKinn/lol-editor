# ADR 0004 — Royalty-free music only, organized into preset pools

- Status: accepted
- Date: 2026-06-24

## Context
The channel is for monetization, and the videos are music-driven (ADR 0003). Copyrighted music
triggers YouTube Content-ID claims, demonetization, or strikes — fatal to the goal. The owner also
wants a mix of editing moods ("hype" for outplays, "funny" for fails/ARAM) at daily volume, so
music selection must be automatic, not hand-picked per clip.

## Decision
Use **royalty-free / licensed music only** — the owner's Artlist subscription (already in use) or
the YouTube Audio Library. Organize tracks into **preset pools** on disk: `music/hype/` and
`music/funny/`. The editor picks a track from the pool matching the clip's preset, so mood follows
the clip with no per-clip choice. Media files are never committed to git.

## Alternatives considered
- **Any music the owner likes:** highest creative freedom, but Content-ID risk kills monetization.
- **A single shared music folder, random pick:** simple, but the mood often won't match the clip
  (hype track on a funny fail) — pools fix this cheaply.
- **Hand-pick per clip:** best fit, but doesn't scale to daily volume.

## Consequences
- Monetization-safe by construction (assuming the Artlist subscription stays active).
- Mood-appropriate music with zero per-clip effort — fits the batch workflow.
- The owner must maintain the pools (drop tracks into the right folder).
- Track licensing is the owner's responsibility to keep valid (e.g. Artlist active).
