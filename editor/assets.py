"""Part 2 — Brand asset generator: build intro.mp4, outro.mp4 and a placeholder logo.png.

This is the code half of the "Hybrid" branding decision (ADR 0011): you source a real
logo yourself (AI / Canva / a designer) and this stage automates the repetitive, must-be-
consistent cards (intro + outro) AROUND it with FFmpeg. Everything is config-driven
([assets] in config.toml). Output goes into assets_dir, where the branding stage
(editor.branding) already looks for intro.mp4 / outro.mp4 / logo.png.

What it writes:
  - logo.png   — ONLY if no logo exists yet: a transparent placeholder with the channel
                 name, so branding has something to overlay today. Once you drop your real
                 logo.png in assets/, re-running this NEVER overwrites it.
  - intro.mp4  — a short title card: the channel name + tagline, the logo above them,
                 faded in and out. Kept short on purpose (long intros lose Shorts viewers).
  - outro.mp4  — an end card with a subscribe call-to-action.

Both cards are silent video — the branding stage injects matching silence when it
concatenates, so a soundless intro/outro joins cleanly (see editor/branding.py).

The cards are built the same way the thumbnail in editor.meta is: a solid background
from FFmpeg's `color` source with `drawtext` burned on top. Text is passed through temp
`textfile=` files (expansion disabled) so any punctuation in the channel name can't be
misread as filter syntax — the same trick meta.py uses to dodge FFmpeg text escaping.

Run it directly:
    python -m editor.assets            # writes intro.mp4, outro.mp4, (placeholder) logo.png
"""

import sys
import tempfile
from pathlib import Path

from editor.config import ROOT, load_config
from editor.ffmpeg import run
from editor.meta import _ff_escape_path   # reuse the Windows drive-colon escaping (ADR 0010)


def _drawtext(textfile: Path, font: str, size: int, color: str, y: str) -> str:
    """One centered drawtext layer reading its text from a temp file (no escaping needed).

    `y` is a drawtext y-expression (e.g. "(h-text_h)/2") so we never have to measure the
    rendered text ourselves — FFmpeg centers it. A black border keeps text legible on any
    background.
    """
    return (
        f"drawtext=fontfile={font}:textfile={_ff_escape_path(textfile)}:expansion=none:"
        f"fontsize={size}:fontcolor={color}:borderw=3:bordercolor=0x000000:"
        f"x=(w-text_w)/2:y={y}"
    )


def _write_textfile(text: str, out_dir: Path) -> Path:
    """Drop a one-line text file in out_dir for drawtext to read. Caller deletes it."""
    tmp = tempfile.NamedTemporaryFile(
        "w", suffix=".txt", dir=str(out_dir), delete=False, encoding="utf-8"
    )
    tmp.write(text)
    tmp.close()
    return Path(tmp.name)


def make_logo_placeholder(logo: Path, cfg: dict) -> None:
    """Write a transparent PNG with the channel name — a stand-in until a real logo exists.

    The background is a fully transparent color source (black@0.0); only the text is
    drawn, so the PNG works as a corner watermark over gameplay. Scaled down by branding
    to [branding].logo_width, so we render it generously here.
    """
    font = _ff_escape_path(Path(str(cfg["font"])))
    tmp_dir = logo.parent
    tf = _write_textfile(cfg["channel_name"], tmp_dir)
    try:
        # colorchannelmixer=aa=0 forces the background alpha to 0 (transparent). This
        # FFmpeg build ignores the `black@0.0` alpha suffix on the color source and
        # `format=rgba` then fills alpha with 255 (opaque) — verified via alphaextract.
        # drawtext runs AFTER, so only the glyph pixels get full alpha back. Without
        # this the logo is an opaque black box over gameplay.
        graph = (
            "[0:v]format=rgba,colorchannelmixer=aa=0,"
            + _drawtext(tf, font, 150, cfg["accent_color"], "(h-text_h)/2")
            + "[v]"
        )
        run([
            "-f", "lavfi", "-i", "color=c=black@0.0:s=900x300",
            "-filter_complex", graph, "-map", "[v]",
            "-frames:v", "1", "-update", "1", str(logo),
        ])
    finally:
        tf.unlink(missing_ok=True)
    print(f"  wrote placeholder {logo.name}  (drop your real logo here to replace it)")


def _render_card(out: Path, lines: list[tuple], duration: float, cfg: dict, logo: Path | None, video_cfg: dict) -> None:
    """Render one silent title card: a colored canvas + stacked drawtext + optional logo.

    `lines` is a list of (text, font_size, color, y_expression). The logo, if given, is
    overlaid centered near the top. The whole card fades in and out.
    """
    w, h = (int(x) for x in str(cfg["resolution"]).lower().split("x"))
    fps = float(cfg["fps"])
    fade = 0.4
    font = _ff_escape_path(Path(str(cfg["font"])))

    tmp_dir = out.parent
    textfiles = [_write_textfile(text, tmp_dir) for (text, _, _, _) in lines]
    try:
        # Stack the text layers on the background canvas.
        layers = [
            _drawtext(tf, font, size, color, y)
            for tf, (_, size, color, y) in zip(textfiles, lines)
        ]
        chain = "[0:v]" + ",".join(layers)

        if logo is not None and logo.exists():
            # Overlay the logo above the text (built AROUND the logo — the Hybrid promise).
            logo_w = w // 6
            logo_y = int(h * 0.12)
            chain += "[base];"
            chain += f"[1:v]scale={logo_w}:-1[lg];"
            chain += f"[base][lg]overlay=(W-w)/2:{logo_y}[ov];"
            tail = "[ov]"
        else:
            chain += ","
            tail = ""

        # Fade in from / out to the background, then lock the pixel format for libx264.
        fades = (
            f"{tail}fade=t=in:st=0:d={fade},"
            f"fade=t=out:st={duration - fade:.3f}:d={fade},format=yuv420p[v]"
        )
        graph = chain + fades

        args = ["-f", "lavfi", "-i", f"color=c={cfg['bg_color']}:s={w}x{h}:r={fps:.6g}"]
        if logo is not None and logo.exists():
            args += ["-i", str(logo)]
        args += [
            "-filter_complex", graph, "-map", "[v]", "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-crf", str(video_cfg["crf"]),
            "-preset", video_cfg["preset"], "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(out),
        ]
        run(args)
    finally:
        for tf in textfiles:
            tf.unlink(missing_ok=True)


def build_assets() -> dict:
    """Generate intro.mp4, outro.mp4 and (if needed) a placeholder logo.png. Returns paths."""
    config = load_config()
    cfg = config["assets"]
    video_cfg = config["video"]
    branding = config["branding"]
    assets_dir = ROOT / config["paths"]["assets_dir"]
    assets_dir.mkdir(parents=True, exist_ok=True)

    name = str(cfg["channel_name"])
    tagline = str(cfg["tagline"])

    # The logo file branding expects (so the placeholder lands where branding looks).
    logo = assets_dir / str(branding.get("logo", "logo.png") or "logo.png")
    if not logo.exists():
        if bool(cfg.get("make_logo_placeholder", True)):
            print("No logo found — generating a placeholder.")
            make_logo_placeholder(logo, cfg)
        else:
            logo = None  # nothing to overlay
    else:
        print(f"Using existing logo: {logo.name}")

    h = int(str(cfg["resolution"]).lower().split("x")[1])

    intro = assets_dir / str(branding.get("intro", "intro.mp4") or "intro.mp4")
    print(f"Rendering intro -> {intro.name}  ({cfg['intro_seconds']}s)")
    _render_card(
        intro,
        [
            (name, h // 8, cfg["accent_color"], "(h-text_h)/2-10"),
            (tagline, h // 26, cfg["text_color"], "(h-text_h)/2+100"),
        ],
        float(cfg["intro_seconds"]), cfg, logo, video_cfg,
    )

    outro = assets_dir / str(branding.get("outro", "outro.mp4") or "outro.mp4")
    logo_in_outro = bool(cfg.get("logo_in_outro", True))
    print(f"Rendering outro -> {outro.name}  ({cfg['outro_seconds']}s)"
          + ("" if logo_in_outro else "  (no logo)"))
    _render_card(
        outro,
        [
            ("Thanks for watching!", h // 22, cfg["text_color"], "(h-text_h)/2-160"),
            (name, h // 8, cfg["accent_color"], "(h-text_h)/2-30"),
            ("Subscribe for more", h // 18, cfg["accent_color"], "(h-text_h)/2+110"),
        ],
        float(cfg["outro_seconds"]), cfg, logo if logo_in_outro else None, video_cfg,
    )

    return {"intro": intro, "outro": outro, "logo": logo}


def main() -> int:
    paths = build_assets()
    for label, p in paths.items():
        if p is not None:
            print(f"Wrote {label}: {p}")
    print("\nBranding will now pick these up. Drop a real logo.png in assets/ and re-run "
          "to rebuild the cards around it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
