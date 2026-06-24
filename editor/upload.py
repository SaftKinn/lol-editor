"""Stage 7 — Upload: push a finished video + its metadata + thumbnail to YouTube.

Input:  a finished video  (output/<name>_edited.mp4  or  output/<name>_branded_short.mp4)
        sidecar JSON      output/<name>_metadata.json   (written by meta.py / Stage 5)
        sidecar thumbnail output/<name>_thumb.png         (written by meta.py / Stage 5)

The stage auto-detects whether the video is a Short (filename ends in _short) and picks
the matching metadata surface (youtube_short vs youtube_long).

Output: the live YouTube URL, printed to stdout.

This stage treats google-api-python-client + google-auth-oauthlib as *optional soft
dependencies* (same pattern as faster-whisper in detect.py). Install once:
    pip install google-api-python-client google-auth-oauthlib

On first run a browser window opens for a one-time OAuth consent (takes ~30 seconds).
Credentials are saved to [youtube].credentials_file so every subsequent run is silent.

Run it directly:
    python -m editor.upload output/my_game_branded.mp4        # long-form
    python -m editor.upload output/my_game_branded_short.mp4  # Short
    python -m editor.upload my_game_branded.mp4               # bare name, resolved in output/
"""

import json
import sys
from pathlib import Path

from editor.config import ROOT, load_config
from editor.edit import _resolve

_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

try:
    import google.oauth2.credentials
    import google.auth.exceptions
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    _GOOGLE_OK = True
except ImportError:
    _GOOGLE_OK = False


def _check_deps() -> None:
    if not _GOOGLE_OK:
        raise SystemExit(
            "google-api-python-client and google-auth-oauthlib are not installed.\n"
            "Run:  pip install google-api-python-client google-auth-oauthlib"
        )


# --- OAuth credentials --------------------------------------------------------

def _creds_path(config: dict) -> Path:
    p = Path(str(config.get("youtube", {}).get(
        "credentials_file", "config/youtube_credentials.json"
    )))
    return p if p.is_absolute() else ROOT / p


def _secrets_path(config: dict) -> Path:
    p = Path(str(config.get("youtube", {}).get(
        "client_secrets", "config/youtube_client_secrets.json"
    )))
    return p if p.is_absolute() else ROOT / p


def _save_credentials(creds, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or _SCOPES),
    }, indent=2), encoding="utf-8")


def _load_credentials(config: dict):
    """Return valid OAuth credentials, running the browser flow if needed."""
    creds_file = _creds_path(config)
    creds = None

    if creds_file.exists():
        data = json.loads(creds_file.read_text(encoding="utf-8"))
        creds = google.oauth2.credentials.Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes"),
        )

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_credentials(creds, creds_file)
            return creds
        except google.auth.exceptions.RefreshError:
            pass  # Token revoked — fall through to the browser flow.

    secrets = _secrets_path(config)
    if not secrets.exists():
        raise SystemExit(
            f"YouTube client secrets not found: {secrets}\n\n"
            "Steps to get them:\n"
            "  1. Open console.cloud.google.com → new project → enable YouTube Data API v3\n"
            "  2. APIs & Services → Credentials → Create → OAuth 2.0 Client ID → Desktop app\n"
            "  3. Download the JSON → save as  config/youtube_client_secrets.json\n"
            "  4. Re-run this command — a browser will open for a one-time login."
        )

    print("Opening browser for YouTube authentication …")
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), _SCOPES)
    creds = flow.run_local_server(port=0)
    _save_credentials(creds, creds_file)
    print(f"Credentials saved to {creds_file}")
    return creds


# --- Sidecar lookup -----------------------------------------------------------

def _find_sidecar(video: Path, suffix: str) -> Path | None:
    """Find a sidecar file next to the video by stripping known suffixes if needed.

    meta.py writes sidecars named after the video it ran on (the master, e.g.
    _branded.mp4).  A Short (_branded_short.mp4) shares the same sidecars, so we
    strip _short from the stem and retry.
    """
    candidate = video.with_name(f"{video.stem}{suffix}")
    if candidate.exists():
        return candidate

    if video.stem.endswith("_short"):
        base_stem = video.stem[:-6]   # strip "_short"
        candidate = video.with_name(f"{base_stem}{suffix}")
        if candidate.exists():
            return candidate

    return None


# --- Hashtag helper (mirrors the one in meta.py) ------------------------------

def _hashtag_line(hashtags: list[str]) -> str:
    clean = [tag.lstrip("#").replace(" ", "") for tag in hashtags if tag.strip()]
    return " ".join(f"#{tag}" for tag in clean)


# --- Core upload --------------------------------------------------------------

def upload_video(video_arg: str, config: dict | None = None) -> str:
    """Upload one video + sidecar metadata + thumbnail to YouTube.

    Returns the YouTube URL of the uploaded video.
    """
    _check_deps()
    if config is None:
        config = load_config()

    video = _resolve(video_arg, ROOT / config["paths"]["output_dir"])
    yt_cfg = config.get("youtube", {})

    is_short = video.stem.endswith("_short")

    # Load the metadata sidecar written by meta.py.
    meta_path = _find_sidecar(video, "_metadata.json")
    if meta_path is None:
        raise SystemExit(
            f"No _metadata.json sidecar found for {video.name}.\n"
            "Run  python -m editor.meta <video>  first to generate it."
        )
    data = json.loads(meta_path.read_text(encoding="utf-8"))

    # Pick the matching metadata surface and build the YouTube fields.
    if is_short:
        surface = data["youtube_short"]
        title = surface["title"]
        hashtags_str = _hashtag_line(surface.get("hashtags", [])) + " #Shorts"
        description = surface["description"].strip() + "\n\n" + hashtags_str
        tags = [h.lstrip("#") for h in surface.get("hashtags", [])] + ["Shorts"]
    else:
        surface = data["youtube_long"]
        title = surface["title"]
        description = surface["description"].strip()
        tags = surface.get("tags", [])

    privacy = str(yt_cfg.get("privacy", "private"))
    category_id = str(yt_cfg.get("category_id", "20"))   # 20 = Gaming
    playlist_id = str(yt_cfg.get("default_playlist", "")).strip()

    creds = _load_credentials(config)
    youtube = build("youtube", "v3", credentials=creds)

    surface_label = "Short" if is_short else "long-form"
    print(f"Uploading {video.name}  ({surface_label}, {privacy})")
    print(f"  Title: {title}")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    # Resumable upload: sends the file in chunks so a network hiccup doesn't
    # mean starting over on a 500 MB clip.
    media = MediaFileUpload(
        str(video), mimetype="video/mp4", resumable=True, chunksize=4 * 1024 * 1024
    )
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  … {pct}%", end="\r", flush=True)

    video_id = response["id"]
    url = f"https://youtu.be/{video_id}"
    print(f"  Upload complete: {url}")

    # Thumbnail — only works on verified/partner channels; fails gracefully otherwise.
    thumb_path = _find_sidecar(video, "_thumb.png")
    if thumb_path:
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumb_path), mimetype="image/png"),
            ).execute()
            print(f"  Thumbnail set from {thumb_path.name}")
        except Exception as exc:   # noqa: BLE001
            print(f"  (thumbnail skipped — channel may not be verified yet: {exc})")

    # Optional playlist assignment.
    if playlist_id:
        try:
            youtube.playlistItems().insert(
                part="snippet",
                body={"snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }},
            ).execute()
            print(f"  Added to playlist {playlist_id}")
        except Exception as exc:   # noqa: BLE001
            print(f"  (playlist add failed: {exc})")

    return url


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m editor.upload <video>")
        print("  e.g. python -m editor.upload output/my_game_branded.mp4")
        print("  e.g. python -m editor.upload output/my_game_branded_short.mp4")
        return 1
    url = upload_video(sys.argv[1])
    print(f"\nDone: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
