# CLAUDE.md

Instructions for any AI assistant (Claude) working in this repository. Read first, every session.

## What this project is

**LoL Editor** (working codename — no brand name yet): a local, code-driven video editor that
turns raw League of Legends clips into finished, upload-ready videos for a **monetization-focused**
YouTube channel — single highlight edits, vertical Shorts, and longer montages — all scored with
royalty-free music and consistently branded (intro/outro + logo).

The owner is a **Darius main** who also captures a lot of **ARAM chaos**. Content angle: highlights
/ montages (hype), funny moments, with a Darius + ARAM identity. The channel is **English-facing**
(titles, overlays, metadata in English), **music-first** for now, with English commentary planned
as a later layer. Goal: growth + monetization. Strategy: **Shorts are the growth funnel; long-form
earns** (Shorts RPM is tiny, long-form CPM is where the money is).

Everything heavy runs **locally** via FFmpeg on the owner's PC. The only paid/cloud part is the
LLM that writes metadata (titles/tags/description) and, later, may help classify clips.

> The owner is a beginner programmer. Favor clear, small steps; explain non-obvious choices;
> prefer simple, readable code over clever code.

## Session ritual

State lives on disk so nothing is lost between sessions.

**At the start of every session, read in this order:**
1. This file (`CLAUDE.md`) — conventions
2. `progress.md` — where we are, what's next
3. The highest-numbered file in `docs/decisions/` — the most recent decision

Then say, in 2–3 sentences: where we are and what we're about to do. Don't change files until
that handshake is done.

**At the end of every working session (do this even if not asked):**
1. Update `progress.md` (`## Current focus`, `## Last session`, `## Next concrete step`,
   `## Open questions`, and the `VERIFY EVIDENCE` line of a phase when its gate is met).
2. On a real decision (a trade-off with alternatives weighed), create the next-numbered ADR in
   `docs/decisions/`.

Trigger words from the owner: `wrap up` or `update progress` = do the end-of-session step now.

## Conventions

- **Languages:** code + docs in **English**. Audience-facing text (titles, captions, overlays,
  thumbnails) is **English** (the channel targets the global market — ADR 0003).
- **Config-driven, never hardcoded.** Paths, music pools, resolution, fps, encoder, preset
  settings all live in a config file. Never hardcode a path.
- **Royalty-free music only.** Use Artlist (the owner's subscription) or the YouTube Audio
  Library. Never commit media files (videos/music) to git — only the code.
- **Separate deterministic work from the LLM.** Cutting, audio mixing, encoding, reframing,
  burning overlays, FFmpeg and file handling = code. Creative text (titles, tags, descriptions,
  thumbnail text) and later content classification = LLM. The LLM never sets timings or does math.
- **File-based, re-runnable stages.** Each stage reads files from a folder and writes files back.
  Any stage can be re-run alone.
- **Local-first.** FFmpeg must be on PATH. Use the GPU encoder (NVENC) for re-encodes at volume.
- **Small commits, one idea each** (once git is set up).

## The pipeline (one line)

Raw clip(s) → (optional highlight detection) → balance game audio + music (ducked) → brand
(intro/outro + logo) → render 16:9 master + cut 9:16 Shorts (blurred-bg fit) + stitch montages →
thumbnail + English metadata → owner uploads.

Full detail in `architecture.md`. The plan and phases are in `roadmap.md`.
