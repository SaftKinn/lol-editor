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
    edit.py          # CORE: balance gameplay + music                        [BUILT]
    presets.py       # pick music from the pool matching the clip's preset   [BUILT]
    branding.py      # prepend intro/outro + overlay a corner logo           [BUILT]
    shorts.py        # reframe to a 9:16 vertical Short (blurred-bg fit)     [BUILT]
    montage.py       # stitch several clips into one long-form video        [BUILT]
    pipeline.py      # batch: run every clip in a folder through the stages  [BUILT]
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

Or drop the clip in a **preset** sub-folder and let the matching music pool be picked
automatically (no music argument needed):

```
python -m editor.edit input/hype/my_game.mp4     # picks a track from music/hype/
python -m editor.edit input/funny/my_game.mp4    # picks a track from music/funny/
```

Within a pool the track is chosen deterministically per clip, so the same clip always
gets the same music (re-runnable). Output lands in `output/`.

Add branding (intro + outro + corner logo) to an edited video — set `intro` / `outro` /
`logo` under `[branding]` in the config and drop the files in `assets/`:

```
python -m editor.branding output/my_game_edited.mp4
```

Make a 9:16 vertical Short from any edit — the full frame stays visible (HUD/minimap
never cropped), with blurred bars top and bottom:

```
python -m editor.shorts output/my_game_edited.mp4
```

Stitch several clips into one long-form montage — pass a folder (all clips, in order)
or an explicit list. One royalty-free track is laid under the whole thing for consistent
audio:

```
python -m editor.montage input/hype/
python -m editor.montage clipA.mp4 clipB.mp4 clipC.mp4
```

Process a whole folder in one go — every clip becomes a master plus a Short, with no
per-clip handwork (the daily-volume workflow):

```
python -m editor.pipeline input/hype/
```

Metadata (titles/tags/description/thumbnail, the LLM stage) is built next.

## What the code does vs. what needs you

- **Code does** (deterministic): trimming, concatenating, mixing + balancing audio,
  looping/ducking music, scaling to 9:16, burning text, encoding upload-ready files.
- **Needs you** (creative): *which* moments are highlights. The tool can't watch the
  footage — for montages you give timestamp ranges (or it falls back to picking the
  loudest moments as a rough proxy for action).
