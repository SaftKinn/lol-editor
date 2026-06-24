# architecture.md — LoL Editor

> Working codename: **LoL Editor** (rename once a channel brand exists). A local, code-driven
> editor that turns raw League of Legends clips into finished, upload-ready videos — single
> highlight edits, vertical Shorts, and montages — scored with royalty-free music and branded.

> Docs and code are English. Audience-facing text (titles, captions, overlays) is English too,
> because the channel targets the global market (ADR 0003).

---

## 1. Overview & design principles

- **One source, many outputs.** Each raw clip can become a 16:9 master, a 9:16 Short, and a piece
  of a longer montage. We never re-edit the same moment by hand per platform. (ADR 0002)
- **Local-first.** All editing is FFmpeg on the owner's GPU/CPU. The only cloud cost is the LLM
  that writes metadata. (ADR 0001)
- **Deterministic vs. creative, kept apart.** Code does the exact, repeatable work (cutting,
  audio mixing, reframing, encoding, burning overlays). The LLM does creative text (titles, tags,
  thumbnail wording) and, later, content classification. The LLM never sets timings. (ADR 0001)
- **Every stage stands alone.** Each stage reads files from a folder and writes files back; any
  one can be run and re-run on its own. (ADR 0001)
- **Built for volume.** The goal is daily Shorts, so the design favors batch processing and
  preset-driven automation over per-clip handwork.
- **Beginner-friendly code.** Simple and readable beats clever.

---

## 2. Hardware & runtime

- **Machine:** the owner's Windows PC — NVIDIA RTX 4070 Super (12 GB VRAM), 32 GB RAM (shared
  with the ORIGIN project).
- **FFmpeg** must be on PATH (already installed, v8.1.1).
- **Encoding:** copy the video stream untouched whenever nothing about the picture changes (just
  swapping audio) — lossless and fast. When a re-encode is needed (Shorts reframe, montage,
  overlays), prefer **NVENC** (`h264_nvenc`) on the 4070 for speed at volume; `libx264` is the
  quality/size fallback. (Encoder is a config setting.)

---

## 3. The pipeline, stage by stage

Each stage writes into a per-video working folder under `output/`. Files are the hand-off between
stages, which is what makes every stage independently re-runnable.

**Stage 0 — Ingest.** Raw clips land in `input/` (primarily **Medal.tv** clips, which are already
short pre-cut highlights; optionally full-game recordings). Clips are sorted by **preset** — for
v1 by sub-folder (`input/hype/`, `input/funny/`) — which selects the editing style and music pool.

**Stage 1 — Core edit (audio + music).** [BUILT] `editor/edit.py`: keep the game audio in front,
lay a royalty-free track underneath (looped to length), **duck** the music when the game gets loud
(sidechain compression), and normalize the final mix to YouTube's −14 LUFS. Video is copied
untouched unless a resize/fps change is requested.

**Stage 2 — Branding.** Add a recognizable intro + outro and a corner logo/watermark. Consistent
across every video. (Owner provides `assets/intro.mp4`, `assets/outro.mp4`, `assets/logo.png`.)

**Stage 3 — Shorts (9:16).** Reframe the 16:9 edit to vertical using a **blurred-background fit**:
the full game frame stays visible in the middle, top/bottom filled with a blurred copy — so the
HUD and minimap at the screen edges are never lost. (ADR 0005)

**Stage 4 — Montage.** Stitch several clips into one longer highlight video for long-form
monetization (the higher-CPM format). Handles intro between clips / transitions.

**Stage 5 — Discovery (LLM).** Generate an English title, tags, and description per video, and a
thumbnail (a frame + bold text). Tuned for click-through and reach. Output mirrors the ORIGIN
project's metadata stage.

**Stage 6 — Batch orchestrator.** Drop many clips in `input/<preset>/`, run one command, get all
outputs (master + Shorts + metadata) for every clip. The engine of the daily-volume workflow.

**Stage 7 — Full-game support (optional).** When the owner records full games, find highlight
moments automatically — primarily via **audio**: LoL's announcer ("Double Kill", "Pentakill",
"Ace") is a fixed set of voice lines detectable with Whisper (reused from ORIGIN), giving precise
timestamps and auto-tags; loudness peaks are a cruder fallback. (See §6 and ADR 0006.)

**Stage 8 — Publish.** Finished video + metadata + thumbnail collected per video; the owner
uploads manually for now. Upload automation (YouTube API) is a later, separately-decided stage.

---

## 4. Project layout

```
lol-editor/
  editor/              # the Python package — one module per stage
    ffmpeg.py          # tiny helpers that run ffmpeg / ffprobe        [BUILT]
    config.py          # reads config/config.toml                      [BUILT]
    edit.py            # Stage 1: balance game audio + music           [BUILT]
    branding.py        # Stage 2: intro/outro + logo                   [planned]
    shorts.py          # Stage 3: 9:16 blurred-bg reframe              [planned]
    montage.py         # Stage 4: stitch clips into long-form          [planned]
    meta.py            # Stage 5: title/tags/description + thumbnail    [planned]
    pipeline.py        # Stage 6: batch orchestrator                   [planned]
    highlights.py      # Stage 7: audio-based highlight detection      [later]
  config/
    config.example.toml
  input/               # raw clips (input/hype/, input/funny/)  — git-ignored media
  music/               # royalty-free tracks (music/hype/, music/funny/) — git-ignored
  assets/              # intro.mp4, outro.mp4, logo.png
  output/              # finished videos + metadata per clip
  docs/decisions/      # ADRs
  CLAUDE.md  architecture.md  roadmap.md  progress.md  README.md
```

---

## 5. Configuration

Everything that changes between runs or machines lives in `config/config.toml`, never hardcoded:
music level + ducking, target loudness, output resolution/fps, encoder (NVENC vs libx264) + CRF +
preset, intro/outro/logo file names, Shorts settings, LLM model + key (for metadata). Paths are
config, not code.

---

## 6. Presets, music & content-understanding

- **Presets** ("hype" / "funny") bundle an editing style + a music pool. v1 selects the preset by
  input sub-folder; the owner can later add AI auto-classification.
- **Music pools.** `music/hype/` and `music/funny/`; the editor picks a track matching the clip's
  preset. Royalty-free only (Artlist / YT Audio Library). (ADR 0004)
- **Content-understanding (later, ADR 0006).** The highest-leverage "understanding" feature is
  cheap and local: detect LoL's announcer voice lines with Whisper to find highlights and
  auto-tag intensity (pentakill, ace, …). A vision LLM on a few sampled frames can classify
  hype/funny and pick a thumbnail moment, but costs scale with daily volume — so it is an
  optional layer, used sparingly.

---

## 7. Out of scope (for now)

- Auto-posting / scheduling to YouTube — the owner uploads by hand (revisit as Stage 8 / Part 2).
- A graphical UI — command-line first.
- English (or any) commentary/voiceover — music-first for now; commentary is a later layer
  (ADR 0003).
- Editing games other than League of Legends.
