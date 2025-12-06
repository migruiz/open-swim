import json
import os
from typing import List

from open_swim.config import config
from open_swim.media.podcast.models import EpisodeRequest, PodcastLibrary


def load_episode_requests() -> List[EpisodeRequest]:
    """Load requested podcast episodes to sync from disk."""
    library_file_path = os.path.join(config.podcasts_library_path, "episodes_to_sync.json")
    if not os.path.exists(library_file_path):
        return []
    with open(library_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [EpisodeRequest(**item) for item in data]


def save_episode_requests(requests: List[EpisodeRequest]) -> None:
    """Persist requested podcast episodes to sync."""
    os.makedirs(config.podcasts_library_path, exist_ok=True)
    library_file_path = os.path.join(config.podcasts_library_path, "episodes_to_sync.json")
    with open(library_file_path, "w", encoding="utf-8") as f:
        json.dump([req.model_dump() for req in requests], f, indent=2, default=str)


def load_library() -> PodcastLibrary:
    """Load podcast library metadata."""
    info_json_path = os.path.join(config.podcasts_library_path, "info.json")
    if not os.path.exists(info_json_path):
        return PodcastLibrary()
    with open(info_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return PodcastLibrary(**data)


def save_library(library: PodcastLibrary) -> None:
    """Persist podcast library metadata."""
    os.makedirs(config.podcasts_library_path, exist_ok=True)
    info_json_path = os.path.join(config.podcasts_library_path, "info.json")
    with open(info_json_path, "w", encoding="utf-8") as f:
        json.dump(library.model_dump(), f, indent=2, default=str)
