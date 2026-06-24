# ADR 0005 — Shorts via blurred-background fit

- Status: accepted
- Date: 2026-06-24

## Context
Shorts (9:16) are the growth funnel (ADR 0002/0003), reframed from 16:9 gameplay. League's UI —
the **minimap, HUD, ability bar, scoreboard** — lives at the screen edges. How the 16:9 frame is
fit into 9:16 decides whether that information survives.

## Decision
Reframe Shorts with a **blurred-background fit**: the full 16:9 game frame is scaled to fit the
width and centered, with the empty top/bottom filled by a blurred, enlarged copy of the same
frame. Nothing is cropped, so the minimap and HUD stay visible.

## Alternatives considered
- **Center crop (zoom in):** fills the vertical screen edge-to-edge and looks "fuller", but crops
  away the minimap and HUD at the edges — bad for LoL, where those carry the context of a play.
- **Gameplay-on-top, blank/text below:** good for reaction/funny formats with a facecam or
  captions, but wastes space when there's no second element; kept as a future per-preset option.

## Consequences
- The whole play (including minimap/HUD) is always visible — safest default for LoL highlights.
- Requires a re-encode (it's not a stream copy), so Shorts use the GPU encoder for speed.
- The blurred bars are less "immersive" than a full crop; acceptable trade for not losing info.
- A crop or top/bottom-split mode can be added later as a per-preset choice.
