import os
import shutil
import glob
from typing import List, Set

from open_swim.config import config
from open_swim.device.sync.state import load_sync_state, save_sync_state
from open_swim.media.podcast import store
from open_swim.media.podcast.episodes_to_sync import load_episodes_to_sync
from open_swim.media.podcast.models import EpisodeRequest


def _get_episode_ids(episodes: List[EpisodeRequest]) -> Set[str]:
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

    episodes_to_sync = load_episodes_to_sync()
    if not episodes_to_sync:
        print("[Podcast Sync] No episodes to sync")
        return

    state = load_sync_state(device_sdcard_path)
    synced_episode_ids = set(state.podcasts.synced_episode_ids)
    episodes_to_sync_ids = _get_episode_ids(episodes_to_sync)

    if episodes_to_sync_ids == synced_episode_ids:
        print("[Podcast Sync] Episodes already up to date on device. Skipping.")
        return

    print("[Podcast Sync] Episode list changed. Syncing to device...")

    _delete_mp3_files(podcast_folder_path)
    library_info = store.load_library()
    sorted_episodes = sorted(episodes_to_sync, key=lambda e: e.date)

    for episode in sorted_episodes:
        if episode.id not in library_info.episodes:
            print(f"[Podcast Sync] Episode {episode.id} not found in library, skipping")
            continue

        episode_info = library_info.episodes[episode.id]
        episode_dir = episode_info.episode_dir

        if not episode_dir or not os.path.exists(episode_dir):
            print(f"[Podcast Sync] Episode directory does not exist: {episode_dir}, skipping")
            continue

        mp3_pattern = os.path.join(episode_dir, "*.mp3")
        mp3_files = sorted(glob.glob(mp3_pattern), key=lambda f: os.path.basename(f))

        for mp3_file in mp3_files:
            filename = os.path.basename(mp3_file)
            destination_path = os.path.join(podcast_folder_path, filename)
            try:
                shutil.copy2(mp3_file, destination_path)
                print(f"[Podcast Sync] Copied: {filename}")
            except Exception as e:
                raise RuntimeError(
                    f"[Podcast Sync] Failed to copy '{filename}' for episode '{episode.id}': {e}"
                ) from e

    state.podcasts.synced_episode_ids = list(episodes_to_sync_ids)
    save_sync_state(state, device_sdcard_path)

    print("[Podcast Sync] Sync completed")
