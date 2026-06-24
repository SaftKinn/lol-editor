# LoL Editor

A small, local, code-driven editor for League of Legends gameplay videos. You drop raw
gameplay clips and royalty-free music in, and it produces upload-ready videos for a
YouTube channel — gameplay audio balanced against background music, optional intro/outro,
vertical Shorts, highlight montages, and text overlays.

Same philosophy as the ORIGIN project: **local-first, config-driven, file-based, every
stage re-runnable.** All editing is deterministic FFmpeg — nothing is uploaded anywhere.

> ⚠️ **Copyright.** Only use royalty-free / licensed music (e.g. the YouTube Audio Library),
> or your uploads will get Content-ID claims, demonetization, or strikes. LoL *gameplay*
> itself is generally fine to upload and monetize under Riot's "Legal Jibber Jabber" policy —
> the music is the risk, not the footage.

## Folder layout

```
lol-editor/
  editor/            # the Python package — one module per editing job
    ffmpeg.py        # tiny helpers that run ffmpeg / ffprobe
    config.py        # reads config/config.toml
    edit.py          # CORE: balance gameplay + music, optional intro/outro  [BUILT]
    shorts.py        # cut 9:16 vertical Shorts                              [planned]
    montage.py       # stitch highlight time-ranges together                [planned]
    overlay.py       # burn text overlays (champion, score, ...)            [planned]
  config/
    config.example.toml   # copy to config.toml and adjust
  input/             # drop raw gameplay videos here
  music/             # drop royalty-free music tracks here
  assets/            # intro.mp4, outro.mp4, logo.png (optional)
  output/            # finished videos land here
```

## Setup

1. FFmpeg must be on PATH (`ffmpeg -version`). It already is on this PC.
2. Copy the config: `config/config.example.toml` -> `config/config.toml`, adjust if needed.
3. Put a gameplay video in `input/` and a royalty-free track in `music/`.

## Use (so far)

Balance one gameplay video against one music track and export an upload-ready file:

```
python -m editor.edit input/my_game.mp4 music/my_track.mp3
```

Output lands in `output/`. The other jobs (Shorts, montage, overlays) are built next,
once the core edit is verified on a real clip.

## What the code does vs. what needs you

- **Code does** (deterministic): trimming, concatenating, mixing + balancing audio,
  looping/ducking music, scaling to 9:16, burning text, encoding upload-ready files.
- **Needs you** (creative): *which* moments are highlights. The tool can't watch the
  footage — for montages you give timestamp ranges (or it falls back to picking the
  loudest moments as a rough proxy for action).
