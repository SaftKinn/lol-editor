# ADR 0012 — Content understanding: Whisper as an optional soft dependency

- Status: accepted
- Date: 2026-06-24

## Context

ADR 0006 deferred AI content-understanding and named Whisper announcer detection as the
"highest-leverage, lowest-cost" first step. The LoL in-game announcer speaks short, fixed
English phrases ("Pentakill!", "Ace!", "First Blood!") at highlight moments — these timestamps
are exactly what a highlight extractor needs. Full-game recordings especially benefit: they
contain many such moments that would otherwise require manual scrubbing.

The core tension: the project rule is "no third-party dependencies, no virtualenv required"
(CLAUDE.md, ADR 0001), but Whisper needs either `openai-whisper` (PyTorch, ~1 GB) or
`faster-whisper` (CTranslate2, ~200 MB). Neither is stdlib.

## Decision

`editor/detect.py` treats `faster-whisper` as an **optional soft dependency**:

```python
try:
    from faster_whisper import WhisperModel
    _WHISPER_OK = True
except ImportError:
    _WHISPER_OK = False
```

If the import fails, `detect.py` prints a one-line install instruction and exits. The rest of
the pipeline (`edit`, `brand`, `shorts`, `montage`, `meta`, `pipeline`) is unaffected — they
never import `detect`.

The stage runs on the **raw clip** (before `edit.py`), not on the edited output. This is
essential: game audio is cleanest before music is mixed in, so Whisper has the best chance of
hearing the announcer over game sounds.

Default model: `base` (~74 MB). It handles short, clearly spoken English phrases reliably.
The owner can switch to `small` or `medium` in `[detect].model` if accuracy needs improvement.
GPU acceleration is opt-in via `[detect].device = "cuda"` (the owner's card already drives
NVENC — CUDA is available).

Output is a JSON sidecar (`output/<name>_moments.json`) with detected timestamps and
pre-computed cut windows (10 s before / 5 s after by default, configurable). A future
`editor/highlights.py` can consume this sidecar directly as a cut list.

## Alternatives considered

- **Whisper CLI via subprocess (like FFmpeg):** clean in principle (no Python import), but
  `openai-whisper` CLI installs PyTorch (1 GB+) and is much heavier than `faster-whisper`.
  The subprocess approach also gives less structured output without extra parsing. Rejected.
- **OpenAI Whisper API via urllib:** zero local deps, consistent with how `meta.py` calls
  Claude. But $0.006/min * daily volume adds up fast, and the whole point of detect.py is
  to be cheap/local. Rejected.
- **FFmpeg loudness peaks (no ML):** free, zero deps, no install. But loudness spikes in LoL
  happen constantly (fights, abilities, pings) — too many false positives to be useful as a
  cut list. Good as a future "cruder fallback" (ADR 0006) but not the primary path.
- **Hard dependency (required):** would block the whole pipeline on installs that take minutes
  and require compiler toolchains on some platforms. Rejected — the pipeline should always run.

## Consequences

- The zero-dep rule is preserved for the core pipeline; detect.py is a clearly-marked optional
  stage that the owner installs separately once, analogous to installing FFmpeg.
- `CLAUDE.md` and `config.example.toml` document the install command and configuration.
- The `_moments.json` sidecar format becomes the interface between detect.py and a future
  `editor/highlights.py` (clip cutting) stage — keep it stable.
- Medal clips have two audio streams (game vs PC audio); detect.py extracts stream 0 (game)
  by default, which is the cleanest source for announcer detection.
