"""Stage: music_fetch.py — download royalty-free music from Freesound into preset pools.

Searches Freesound.org by preset-specific keywords, filters by license (CC0 by default)
and duration, and saves the high-quality MP3 preview into music/<preset>/. The pipeline
picks up any new files automatically on the next run.

Freesound API key required — free registration at freesound.org/apiv2/apply/.
Set the key as an environment variable (or point env_file in config to a .env file):
    set FREESOUND_API_KEY=your_key_here

Usage:
    python -m editor.music_fetch              # fetch for all presets in config
    python -m editor.music_fetch hype         # fetch for one preset
    python -m editor.music_fetch hype funny   # fetch for specific presets
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from editor.config import ROOT, load_config

_BASE = "https://freesound.org/apiv2"


def _load_api_key(config: dict) -> str:
    """Read the Freesound API key from an env var or a .env file."""
    import os
    fc      = config.get("music_fetch", {})
    env_var = str(fc.get("api_key_env", "FREESOUND_API_KEY"))
    key     = os.environ.get(env_var, "")

    if not key:
        env_file = str(fc.get("env_file", ""))
        if env_file:
            try:
                for line in Path(env_file).read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        if k.strip() == env_var:
                            key = v.strip().strip('"').strip("'")
                            break
            except FileNotFoundError:
                pass

    if not key:
        raise SystemExit(
            f"Freesound API key not found in env var '{env_var}'.\n"
            f"Get a free key at: https://freesound.org/apiv2/apply/\n"
            f"Then run:  set {env_var}=your_key_here\n"
            f"Or add env_file to [music_fetch] in config to reuse a .env file."
        )
    return key


def _search(query: str, api_key: str, license_filter: str,
            min_dur: float, max_dur: float, page_size: int) -> list[dict]:
    """Return raw Freesound search result dicts."""
    filter_str = f'license:"{license_filter}" duration:[{min_dur} TO {max_dur}]'
    params = urllib.parse.urlencode({
        "query":     query,
        "filter":    filter_str,
        "fields":    "id,name,username,license,duration,previews",
        "sort":      "downloads_desc",   # most-downloaded first → battle-tested tracks
        "page_size": page_size,
        "token":     api_key,
    })
    url = f"{_BASE}/search/text/?{params}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode()).get("results", [])
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Freesound API error {e.code}: {e.reason}\n"
                         f"Check your API key and try again.")


def fetch_preset(preset: str, config: dict, music_dir: Path, api_key: str) -> int:
    """Download tracks for one preset into music/<preset>/. Returns count of new files."""
    fc        = config.get("music_fetch", {})
    queries   = fc.get("queries", {})
    query     = str(queries.get(preset, f"epic gaming {preset}"))
    license_f = str(fc.get("license", "Creative Commons 0"))
    min_dur   = float(fc.get("min_duration", 60))
    max_dur   = float(fc.get("max_duration", 360))
    n         = int(fc.get("tracks_per_preset", 5))

    out_dir = music_dir / preset
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f'\n[{preset}]  query: "{query}"')
    sounds = _search(query, api_key, license_f, min_dur, max_dur, page_size=min(n * 3, 30))

    if not sounds:
        print(f"  No results — adjust [music_fetch.queries].{preset} in config.")
        return 0

    new = 0
    for s in sounds[:n]:
        preview_url = s.get("previews", {}).get("preview-hq-mp3", "")
        if not preview_url:
            continue

        safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in s["name"])
        safe = safe.strip().replace(" ", "_")[:60]
        dest = out_dir / f"{s['id']}_{safe}.mp3"

        mins = int(s["duration"] // 60)
        secs = int(s["duration"] % 60)

        if dest.exists():
            print(f"  skip  {dest.name}  ({mins}:{secs:02d})")
            continue

        print(f"  dl    {dest.name}  ({mins}:{secs:02d})  by {s['username']}")
        urllib.request.urlretrieve(preview_url, dest)
        new += 1

    return new


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    config    = load_config()
    music_dir = ROOT / config["paths"]["music_dir"]
    presets   = list(argv) if argv else config.get("presets", {}).get("names", [])

    if not presets:
        print("No presets given and none found in config[presets][names].", file=sys.stderr)
        return 1

    api_key = _load_api_key(config)
    total   = 0
    for preset in presets:
        total += fetch_preset(str(preset), config, music_dir, api_key)

    print(f"\nDone — {total} new track(s) downloaded.")
    if total:
        print("Run the pipeline and they will be picked up automatically.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
