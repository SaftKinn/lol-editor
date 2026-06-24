# ADR 0007 — Deterministic per-clip track selection within a music pool

- Status: accepted
- Date: 2026-06-24

## Context
ADR 0004 decided that music lives in preset pools (`music/hype/`, `music/funny/`) and the editor
picks a track from the pool matching the clip's preset, with no per-clip choice. Phase 2 implements
that pick. The open question was *how* to pick one track from a pool of several. A core project
principle is that **every stage is re-runnable and reproducible** (ADR 0001): re-running the edit on
the same clip should produce the same output.

## Decision
Select the track by a **stable hash of the clip's file name** mapped to an index into the pool's
**sorted** track list (`editor/presets.py`: `_pick` / `choose_music`). Concretely:
`index = int(md5(clip_stem), 16) % len(tracks)`.

This makes the choice **deterministic per clip** — the same clip always gets the same track, so
re-runs are byte-stable — while **different clips spread across the pool**, giving variety at
batch volume without any per-clip handwork.

We use `hashlib.md5`, **not** Python's built-in `hash()`, because the built-in string hash is
salted per process (`PYTHONHASHSEED`) and would pick a different track on each run — breaking
reproducibility. md5 here is a stable name→index mapper, not security.

A clip placed directly in `input/` (no preset sub-folder) draws from the top-level `music/` folder;
an empty preset pool falls back to that same top-level folder so a missing pool degrades gracefully
instead of failing a batch.

## Alternatives considered
- **`random.choice` per run:** maximal variety, but a different track every re-run — breaks the
  re-runnable/reproducible principle. Rejected.
- **First track alphabetically:** fully deterministic, but every clip in a preset gets the *same*
  track — no variety across a batch. Rejected.
- **Round-robin / a persisted counter:** good spread, but needs mutable state on disk and makes the
  result depend on processing order rather than the clip itself — not re-runnable in isolation.
- **Seeded random from the clip name:** equivalent to the hash approach; the direct hash is simpler
  and has no RNG-implementation dependency.

## Consequences
- Re-running `editor.edit` on a clip is reproducible; the music never changes underneath a clip.
- Variety across a batch comes for free as long as pools hold more than one track.
- Renaming a clip changes its track (the name is the key) — acceptable and predictable.
- The owner must keep pools stocked with royalty-free tracks (ADR 0004); selection logic does not
  validate licensing.
