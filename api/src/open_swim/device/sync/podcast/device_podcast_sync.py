import os
import json
import shutil
import glob
from typing import List, Set

from open_swim.config import config
from open_swim.media.podcast.episodes_to_sync import EpisodeToSync, load_episodes_to_sync
from open_swim.media.podcast.sync import load_library_info


def _load_synced_episodes(podcast_folder_path: str) -> List[EpisodeToSync]:
    """Load synced_episodes.json from device if it exists."""
    synced_json_path = os.path.join(podcast_folder_path, "synced_episodes.json")
    if os.path.exists(synced_json_path):
        with open(synced_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [EpisodeToSync(**item) for item in data]
    return []


def _save_synced_episodes(podcast_folder_path: str, episodes: List[EpisodeToSync]) -> None:
    """Save synced episodes list to device."""
    synced_json_path = os.path.join(podcast_folder_path, "synced_episodes.json")
    with open(synced_json_path, "w", encoding="utf-8") as f:
        json.dump([episode.model_dump() for episode in episodes], f, default=str, indent=2)
    print(f"[Podcast Sync] Saved synced episodes to {synced_json_path}")


def _get_episode_ids(episodes: List[EpisodeToSync]) -> Set[str]:
    """Extract episode IDs from a list of episodes."""
    return {episode.id for episode in episodes}


def _delete_mp3_files(podcast_folder_path: str) -> None:
    """Delete all MP3 files from the podcast folder."""
    mp3_pattern = os.path.join(podcast_folder_path, "*.mp3")
    mp3_files = glob.glob(mp3_pattern)
    for mp3_file in mp3_files:
        os.remove(mp3_file)
        print(f"[Podcast Sync] Deleted: {os.path.basename(mp3_file)}")


def sync_podcast_episodes_to_device() -> None:
    """Sync podcast episodes from library to device."""
    device_sdcard_path = config.device_sd_path

    if not device_sdcard_path:
        print("[Podcast Sync] OPEN_SWIM_SD_PATH environment variable not set")
        return

    if not os.path.exists(device_sdcard_path):
        print(f"[Podcast Sync] Device SD card path does not exist: {device_sdcard_path}")
        return

    podcast_folder_path = os.path.join(device_sdcard_path, "podcast")
    if not os.path.exists(podcast_folder_path):
        print(f"[Podcast Sync] Podcast folder does not exist: {podcast_folder_path}")
        return

    # Load episodes to sync from library
    episodes_to_sync = load_episodes_to_sync()
    if not episodes_to_sync:
        print("[Podcast Sync] No episodes to sync")
        return

    # Load currently synced episodes from device
    synced_episodes = _load_synced_episodes(podcast_folder_path)

    # Compare episode IDs
    episodes_to_sync_ids = _get_episode_ids(episodes_to_sync)
    synced_episode_ids = _get_episode_ids(synced_episodes)

    if episodes_to_sync_ids == synced_episode_ids:
        print("[Podcast Sync] Episodes already up to date on device. Skipping.")
        return

    print("[Podcast Sync] Episode list changed. Syncing to device...")

    # Delete all existing MP3 files from podcast folder
    _delete_mp3_files(podcast_folder_path)

    # Load library info to get episode directories
    library_info = load_library_info()

    # Sort episodes by date ascending
    sorted_episodes = sorted(episodes_to_sync, key=lambda e: e.date)

    # Copy MP3 files from library to device (ordered by episode date, then filename)
    for episode in sorted_episodes:
        if episode.id not in library_info.episodes:
            print(f"[Podcast Sync] Episode {episode.id} not found in library, skipping")
            continue

        episode_info = library_info.episodes[episode.id]
        episode_dir = episode_info.episode_dir

        if not os.path.exists(episode_dir):
            print(f"[Podcast Sync] Episode directory does not exist: {episode_dir}, skipping")
            continue

        # Get and sort MP3 files by filename (001, 002, 003...)
        mp3_pattern = os.path.join(episode_dir, "*.mp3")
        mp3_files = sorted(glob.glob(mp3_pattern), key=lambda f: os.path.basename(f))

        for mp3_file in mp3_files:
            filename = os.path.basename(mp3_file)
            destination_path = os.path.join(podcast_folder_path, filename)
            try:
                shutil.copy2(mp3_file, destination_path)
                print(f"[Podcast Sync] Copied: {filename}")
            except Exception as e:
                print(f"[Podcast Sync] Error copying {filename}: {e}")

    # Save synced episodes list to device
    _save_synced_episodes(podcast_folder_path, episodes_to_sync)

    print("[Podcast Sync] Sync completed")
