import json
import os
from typing import List

from open_swim.config import config
from open_swim.media.youtube.models import PlaylistRequest, YouTubeLibrary


def load_playlist_requests() -> List[PlaylistRequest]:
    """Load requested playlists to sync from disk."""
    library_file_path = os.path.join(config.youtube_library_path, "playlists_to_sync.json")
    if not os.path.exists(library_file_path):
        return []
    with open(library_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [PlaylistRequest(**item) for item in data]


def save_playlist_requests(requests: List[PlaylistRequest]) -> None:
    """Persist requested playlists to sync."""
    os.makedirs(config.youtube_library_path, exist_ok=True)
    library_file_path = os.path.join(config.youtube_library_path, "playlists_to_sync.json")
    with open(library_file_path, "w", encoding="utf-8") as f:
        json.dump([req.model_dump() for req in requests], f, indent=2, default=str)


def load_library() -> YouTubeLibrary:
    """Load YouTube library metadata."""
    info_json_path = os.path.join(config.youtube_library_path, "info.json")
    if not os.path.exists(info_json_path):
        return YouTubeLibrary()
    with open(info_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return YouTubeLibrary(**data)


def save_library(library: YouTubeLibrary) -> None:
    """Persist YouTube library metadata."""
    os.makedirs(config.youtube_library_path, exist_ok=True)
    info_json_path = os.path.join(config.youtube_library_path, "info.json")
    with open(info_json_path, "w", encoding="utf-8") as f:
        json.dump(library.model_dump(), f, indent=2, default=str)
