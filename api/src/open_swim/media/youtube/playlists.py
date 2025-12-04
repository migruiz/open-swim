import json
import os
import subprocess
from typing import List, Optional

from pydantic import BaseModel, Field


class YoutubeVideo(BaseModel):
    id: str
    title: str
    url: str = ""


class PlaylistInfo(BaseModel):
    id: str
    title: str
    uploader: Optional[str] = None
    uploader_id: Optional[str] = None
    playlist_count: int = Field(default=0, alias="_playlist_count")
    videos: List[YoutubeVideo] = Field(default_factory=list)


def fetch_playlist_information(playlist_url: str, playlist_title: str) -> PlaylistInfo:
    """
    Extract playlist information from a YouTube playlist URL using yt-dlp.
    Raises ValueError or RuntimeError on error.
    """
    if not playlist_url:
        raise ValueError("Playlist URL is required!")

    is_valid_playlist = (
        "youtube.com" in playlist_url
        and ("playlist?list=" in playlist_url or "&list=" in playlist_url)
    )
    if not is_valid_playlist:
        raise ValueError("Invalid YouTube playlist URL")

    try:
        yt_dlp_cmd = os.getenv("YTDLP_PATH", "yt-dlp")
        print(f"Extracting playlist {playlist_title} info from URL: {playlist_url}")
        command = [yt_dlp_cmd, "--dump-single-json", "--flat-playlist", playlist_url]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
        )

        stdout = result.stdout
        stderr = result.stderr

        if stderr and not stdout:
            print(f"yt-dlp error: {stderr}")
            raise RuntimeError("Failed to fetch playlist information")

        data = json.loads(stdout.strip())

        videos: List[YoutubeVideo] = []
        for entry in data.get("entries", []):
            if not entry:
                continue

            video = YoutubeVideo(
                id=entry.get("id", ""),
                title=entry.get("title", "Unknown Title"),
                url=entry.get("url", f"https://www.youtube.com/watch?v={entry.get('id', '')}"),
            )
            videos.append(video)

        playlist_info = PlaylistInfo(
            id=data.get("id", ""),
            title=data.get("title", "Unknown Playlist"),
            uploader=data.get("uploader"),
            uploader_id=data.get("uploader_id"),
            _playlist_count=data.get("playlist_count", len(videos)),
            videos=videos,
        )

        return playlist_info

    except subprocess.TimeoutExpired:
        raise RuntimeError("Request timeout while fetching playlist") from None
    except json.JSONDecodeError as exc:
        print(f"Failed to parse JSON output: {exc}")
        raise RuntimeError("Failed to parse playlist information") from exc
    except Exception:
        raise
