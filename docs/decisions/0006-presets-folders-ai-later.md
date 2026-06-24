# ADR 0006 — Folder-based presets now; AI content-understanding later

- Status: accepted
- Date: 2026-06-24

## Context
Each clip needs a "preset" (hype vs funny) that selects its editing style + music pool (ADR 0004).
The owner asked whether a tool could *understand the video content* to classify clips and generate
better videos automatically. That is possible, but at the target of **daily volume**, any approach
that pays per clip must be weighed against cost.

## Decision
For v1, assign the preset **by input sub-folder** (`input/hype/`, `input/funny/`) — zero cost,
fully reliable, no per-clip API spend. Treat **AI content-understanding as a later enhancement**,
layered in roughly cost order:
1. **Whisper announcer detection** (cheap, local, reuses ORIGIN's faster-whisper): LoL's announcer
   speaks fixed lines ("Double Kill", "Pentakill", "Ace", "First Blood") — detect them to find
   highlight timestamps in full games and auto-tag intensity. Highest leverage for the least cost.
2. **Loudness peaks** as a cruder, free fallback for action.
3. **Vision LLM on a few sampled frames** to classify hype/funny, pick a thumbnail moment, and
   sharpen titles — used sparingly, since cost scales with frames × clips at daily volume.

## Alternatives considered
- **Vision-LLM classification from day one:** "smartest", but pays per clip every day before the
  basics even exist — premature spend; deferred.
- **Filename tags / a single default with manual override:** also zero cost, but sub-folders are
  the cleanest fit for dropping a batch of clips by mood.
- **Riot API / kill-feed OCR for events:** powerful but brittle on arbitrary recorded mp4s, and
  unnecessary while Medal already pre-clips highlights.

## Consequences
- Productive immediately with no per-clip AI cost; the "smart" layer is additive, not a blocker.
- Whisper announcer detection becomes the natural first content-understanding feature when
  full-game support lands (it reuses tooling the owner already has from ORIGIN).
- Until AI classification exists, the owner sorts clips into hype/funny folders by hand (cheap).
