# ADR 0010 — Discovery stage: stdlib LLM client, preset-driven metadata, FFmpeg thumbnail

- Status: accepted
- Date: 2026-06-24

## Context
Stage 5 (discovery) is the only LLM stage and the only paid/cloud part of the pipeline
(ADR 0001). It must write an English title + tags + description per video and a thumbnail.
Three sub-decisions came up while building it.

1. **How to call Claude.** The recommended path is the official `anthropic` SDK, but the
   project has a hard rule — *no third-party dependencies* (only the standard library +
   FFmpeg today). The sibling "ORIGIN" project (`SocialMedia Projekt`) uses the SDK +
   `python-dotenv`; we deliberately diverge.
2. **What the metadata is based on.** Unlike ORIGIN, we have no narration script — this is
   a music-first gameplay channel. There is no transcript and no frame analysis yet.
3. **How to build the thumbnail** while keeping the deterministic/creative split (ADR 0001).

## Decision
**1. Call the Claude API directly over HTTPS with `urllib` (standard library).** No SDK, no
`pip install`, honoring the zero-dependency rule. The call lives in `editor/meta.py`
(`call_claude`) and uses structured outputs (`output_config.format` + a JSON schema) so the
reply is guaranteed-valid JSON — no fragile prompt-parsing. Model is config-driven
(`[llm].model`, default `claude-sonnet-4-6` — "start cheap with Sonnet", flip to
`claude-opus-4-8` for quality runs). The API key is read from an environment variable
(`[llm].api_key_env`, default `ANTHROPIC_API_KEY`) so it never lands in git; an optional
`[llm].env_file` lets the owner reuse a key already stored elsewhere without copying it.

**2. Generate metadata from the preset + file name + duration (honest v1).** With no
transcript or vision, the LLM is told it has none and asked to write engaging League of
Legends highlight metadata that fits the clip's preset (hype/funny) and the channel identity
(Darius main + ARAM chaos). Real content understanding — Whisper announcer detection and a
vision LLM on sampled frames — stays deferred to Part 2 (ADR 0006).

**3. Thumbnail = deterministic FFmpeg frame grab + LLM overlay text.** Code grabs a still at a
configurable fraction of the clip (`[thumbnail].frame_at`, scaled to 1280x720) and burns the
LLM's short `thumbnail_text` onto it with `drawtext`. The LLM writes only the wording; the
frame choice, scaling and overlay are code. Output is flat sibling files next to the video
(`<name>_metadata.md`, `<name>_metadata.json`, `<name>_thumb.png`) — consistent with the
existing `_edited` / `_short` naming rather than a new per-video folder.

## Alternatives considered
- **`anthropic` SDK (like ORIGIN):** simplest and most robust, but adds the first third-party
  dependency + a pip/requirements step. Rejected to keep the project install-free; the
  metadata call is a single POST, so the SDK buys little here.
- **Put the API key in `config.toml`:** convenient but the key would live in a file that must
  be kept out of git. Rejected in favour of an env var (with an optional env_file escape
  hatch for reusing an existing key).
- **Wait for transcript/vision before writing metadata:** higher quality, but blocks the only
  remaining stage behind Part 2. Rejected — preset-driven metadata is useful now and the
  richer signal can be layered in later without changing the stage's shape.
- **Per-video output folder (`output/<name>/`):** matches the roadmap's gate wording, but
  would restructure every existing stage's flat output. Rejected for v1; flat sibling files
  meet the intent (video + metadata + thumbnail together) and stay re-runnable.

## Consequences
- The pipeline stays dependency-free; `python -m editor.meta <video>` runs with only stdlib +
  FFmpeg + a key in the environment.
- Metadata quality is bounded by having no transcript/vision; it is on-brand and honest but
  generic per preset until Part 2 adds content understanding.
- One FFmpeg-on-Windows gotcha is baked into `_ff_escape_path`: the drive colon must be
  escaped as `\\:` (two backslashes) for `drawtext`, because it is unescaped twice (filtergraph
  parser, then the option parser). A single backslash silently splits the option.
- `editor/pipeline.py` now runs metadata per clip (after Shorts); a missing key is caught and
  treated as "skip", like branding with no assets — one missing key never kills a batch.
- The LLM is non-deterministic, so re-running `meta` rewrites different (still on-brand) text.
  Unlike the deterministic stages, this stage is re-runnable but not bit-identical.
