import json
import shutil
import os
import tempfile
from pathlib import Path
import re
import queue
import threading
from typing import Callable, Dict, List

import requests
from pydantic import BaseModel

from open_swim.media.podcast.episode_processor import get_episode_segments
from open_swim.media.podcast.episodes_to_sync import EpisodeToSync, load_episodes_to_sync

class EpisodeMp3Info(BaseModel):
    id: str
    title: str
    episode_dir: str


class LibraryData(BaseModel):
    episodes: Dict[str, EpisodeMp3Info]

    @classmethod
    def from_dict(cls, episodes: dict) -> "LibraryData":
        """Parse the JSON structure where keys are the episode IDs"""
        return cls(episodes=episodes)


LIBRARY_PATH = os.getenv('LIBRARY_PATH', '/library')
podcasts_library_path = os.path.join(LIBRARY_PATH, "podcasts")



def sync_podcast_episodes() -> None:
    """Sync multiple podcast episodes by processing each one."""
    episodes = load_episodes_to_sync()
    for episode in episodes:        
        _process_podcast_episode(
            episode=episode)




def _process_podcast_episode(episode: EpisodeToSync) -> None:
    """Process a podcast episode by downloading, splitting, adding intros, and merging segments."""
    library_info = _load_library_info()
    if episode.id in library_info.episodes:
        print(f"Episode {episode.id} already processed. Skipping.")
        return
    
    # Create a temporary directory for processing
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Download the podcast
        print(f"Downloading podcast from {episode.download_url}...")
        episode_path = _download_podcast(
            url=episode.download_url, output_dir=tmp_path)

        final_segments = get_episode_segments(
            episode=episode,
            episode_path=episode_path,
            tmp_path=tmp_path,
        )

        episode_dir = _get_library_episode_directory(episode)
        _copy_episode_segments_to_library(
            episode_dir=episode_dir, segments_paths=final_segments)
        
        library_info.episodes[episode.id] = EpisodeMp3Info(
            id=episode.id,
            title=episode.title,
            episode_dir=str(episode_dir)
        )
        _save_library_info(library_info)
        print(
            f"Processing complete! Generated {len(final_segments)} segments.")


def _get_library_episode_directory(episode: EpisodeToSync) -> Path:
    episode_folder = episode.title + "_" + episode.id
    episode_folder = re.sub(r'[^\w\s-]', '', episode_folder)
    episode_folder = re.sub(r'[\s]+', '_', episode_folder.strip())
    episode_dir = Path(podcasts_library_path) / episode_folder
    return episode_dir


def _save_library_info(library_data: LibraryData) -> None:
    info_json_path = os.path.join(podcasts_library_path, "info.json")
    with open(info_json_path, "w", encoding="utf-8") as f:
        json.dump(library_data.model_dump(), f, indent=2)
    print(f"[Info JSON] Saved library info to {info_json_path}")


def _load_library_info() -> LibraryData:
    info_json_path = os.path.join(podcasts_library_path, "info.json")
    if os.path.exists(info_json_path):
        with open(info_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return LibraryData.from_dict(data["episodes"])
    else:
        print("[Info JSON] info.json does not exist in /library/")
        return LibraryData(episodes={})


def _copy_episode_segments_to_library(episode_dir: Path, segments_paths: List[Path]) -> None:

    episode_dir.mkdir(parents=True, exist_ok=True)
    for segment_path in segments_paths:
        destination = episode_dir / segment_path.name
        shutil.copy2(segment_path, destination)


def _download_podcast(url: str, output_dir: Path) -> Path:
    """Download podcast from the given URL.
    Returns the path to the downloaded file."""

    response = requests.get(url, stream=True)
    response.raise_for_status()

    # Generate filename from URL or use a default
    filename = (url.split('/')[-1] or 'podcast.mp3')[:18]
    if not filename.endswith('.mp3'):
        filename += '.mp3'

    output_path = output_dir / filename

    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return output_path
