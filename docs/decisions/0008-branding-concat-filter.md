# ADR 0008 — Branding via the concat filter + overlay (re-encode), not stream-copy

- Status: accepted
- Date: 2026-06-24

## Context
Stage 2 (branding) prepends an intro, appends an outro, and overlays a corner logo so every video
is recognizably the channel's (ADR 0002). Intro/outro are arbitrary files the owner supplies — they
will not match the gameplay clip's resolution, fps, codec, SAR, or audio layout, and an intro/outro
may have no audio track at all. FFmpeg offers two ways to join clips: the **concat demuxer**
(stream copy, no re-encode) and the **concat filter** (decodes + re-encodes).

## Decision
Join the clips with the **concat filter** in `editor/branding.py`. Each clip is normalized to one
canvas before concatenation: `scale ... force_original_aspect_ratio=decrease` + `pad` (fit-and-
letterbox, so a differently-shaped intro is never stretched), `setsar=1`, a fixed `fps`, and
`format=yuv420p`; audio is resampled to 48 kHz stereo. The logo is scaled and `overlay`'d over the
whole concatenated result, positioned by a config-driven corner + margin, with optional opacity.

The target canvas is the **main clip's** own resolution/fps (or explicit `[video]` settings if set),
so branding never changes the gameplay's look — the intro/outro adapt to the clip, not vice-versa.

A clip with **no audio stream** gets a matching length of `anullsrc` silence injected (trimmed to
its probed duration), because the concat filter requires every segment to carry both video and audio.

Branding is therefore always a re-encode, using the existing `[video]` libx264 settings. That cost is
unavoidable here: overlaying the logo already rewrites every frame.

## Alternatives considered
- **Concat demuxer (stream copy):** near-instant and lossless, but requires *identical* codec
  parameters across all clips — it silently corrupts or refuses on mismatched intro/outro. Brittle
  for arbitrary assets; rejected as the default. (Could be a fast path later if assets are
  pre-normalized to the channel's exact spec.)
- **Pre-normalize intro/outro once, then stream-copy concat:** faster per render, but adds a manual
  asset-prep step and a second spec to keep in sync; premature while volume is low.
- **Overlay the logo only on the main clip, not intro/outro:** the architecture says "logo
  throughout"; overlaying the whole concatenated video is simpler and matches that intent. The owner
  can leave the logo unset if an intro already carries branding.

## Consequences
- Robust against any intro/outro the owner drops in — mixed resolution/fps/codec/silent all just work.
- Every branded render re-encodes (slower than the Stage 1 copy path); acceptable since the logo
  overlay forces it. Encoder is still the config's libx264; NVENC remains an open optimization for
  the re-encode stages at volume.
- Gameplay look is preserved; intro/outro letterbox into the clip's frame rather than reshaping it.
- Branding cannot run until the owner provides real assets and a channel brand (still open) — the
  pipeline was verified with synthetic intro/outro/logo (mixed res + a silent outro) and the
  intro/outro/logo all appeared correctly in the output.
