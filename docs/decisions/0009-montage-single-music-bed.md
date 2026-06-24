# ADR 0009 — Montage lays one music bed for consistent audio

- Status: accepted
- Date: 2026-06-24

## Context
Stage 4 (montage) stitches several clips into one long-form video — the higher-CPM format that
earns (ADR 0002). The verification gate is "plays start to finish with **consistent audio**". If the
montage simply concatenates already-edited clips, each clip carries its own music track that starts
and stops at every cut — jarring, and not how a long-form highlight reel should sound. Some source
clips also have no audio at all (e.g. a silent recording), which would leave gaps.

## Decision
By default the montage lays **one royalty-free track under the whole video**: concatenate the clips'
game audio, then mix a single bed beneath it, ducked + normalized to −14 LUFS using the *same*
`build_audio_filter` as the core edit (config `[montage].music_bed = true`). The bed is picked from
the clips' preset pool via `presets.choose_music`, so a hype montage gets hype music. Clips with no
audio get matching silence injected before concat, so the game-audio track stays aligned and the bed
plays continuously over them.

Setting `music_bed = false` keeps each clip's own audio untouched — useful when the clips are raw
game-audio captures you want to hear straight, or already share one continuous track.

The clips themselves are joined with the concat filter and normalized to a common canvas, exactly as
in branding (ADR 0008), so mixed-resolution/fps/codec clips stitch cleanly.

## Alternatives considered
- **Concatenate edited clips, keep their per-clip music:** zero extra work, but the music resets at
  every cut — fails the "consistent audio" intent. Rejected as the default.
- **No music, game audio only:** clean but flat for a hype reel, and breaks on silent source clips.
  Kept as the `music_bed = false` option.
- **Crossfade/xfade transitions between clips:** nicer visually, but xfade needs per-clip offset math
  and chains awkwardly for N clips; deferred as a later enhancement. v1 uses hard cuts.

## Consequences
- Long-form montages sound like one continuous piece, even across silent clips — matches the gate.
- Reuses the edit stage's ducking/loudness verbatim (one place to tune audio behavior).
- The bed pick is deterministic (ADR 0007), keyed off the montage output name.
- Hard cuts only for now; transitions are a future per-preset option.
- Re-encodes (concat filter + audio mix); encoder is still libx264, NVENC remains the open
  volume optimization.
