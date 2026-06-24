# ADR 0001 — Local-first, FFmpeg, config-driven, file-based re-runnable stages

- Status: accepted
- Date: 2026-06-24

## Context
The owner wants to produce a high volume of LoL videos for a monetization-focused channel, on a
capable Windows PC (RTX 4070 Super), and is a beginner programmer. The work is batch video
editing, not anything latency-sensitive.

## Decision
Build the editor as small, independent Python stages that shell out to **FFmpeg**, run **locally**,
are driven by a **config file** (not hardcoded paths/settings), and hand off via **files** in a
per-video folder so any stage can be run and re-run on its own. Deterministic work (cutting, audio
mixing, reframing, encoding, overlays) is code; only creative text (metadata) and later content
classification go to an LLM. This mirrors the owner's ORIGIN project, which already works this way.

## Alternatives considered
- **A cloud editing service / API:** per-use cost, upload dependency, less control — wrong for a
  high-volume, local-capable, cost-sensitive setup.
- **A monolithic one-shot script:** simpler to start, but can't re-run a single stage, hard to
  debug, and doesn't scale to batch.
- **A GUI editor (Premiere/DaVinci) by hand:** doesn't scale to daily volume and isn't automatable.

## Consequences
- Zero marginal cost per video except the small LLM metadata call; full control; reproducible.
- Each stage is independently testable and re-runnable — easy to fix one thing without redoing all.
- Requires FFmpeg on PATH and some FFmpeg knowledge encoded in the helpers.
- Same conventions as ORIGIN, so the owner only learns one mental model.
