import os
import glob
from typing import Dict, List, Tuple

from open_swim.config import config
from open_swim.device.sync.files import copy_failures_message, copy_file_to_device, device_name
from open_swim.device.sync.state import load_sync_state, save_sync_state
from open_swim.media.podcast import store
from open_swim.media.podcast.episodes_to_sync import load_episodes_to_sync
from open_swim.media.podcast.models import EpisodeRequest, PodcastLibrary


def _episodes_ready_in_library(
    episodes: List[EpisodeRequest], library_info: PodcastLibrary
) -> List[Tuple[EpisodeRequest, str]]:
    """Requested episodes whose processed segments exist, paired with their folder."""
    ready: List[Tuple[EpisodeRequest, str]] = []
    for episode in episodes:
        episode_info = library_info.episodes.get(episode.id)
        if episode_info is None:
            print(f"[Podcast Sync] Episode {episode.id} not found in library, skipping")
            continue
        episode_dir = episode_info.episode_dir
        if not episode_dir or not os.path.exists(episode_dir):
            print(f"[Podcast Sync] Episode directory does not exist: {episode_dir}, skipping")
            continue
        ready.append((episode, episode_dir))
    return ready


def _parts_to_copy(episode: EpisodeRequest, episode_dir: str) -> List[str]:
    """The episode's parts from its start part on, in order; earlier ones are heard."""
    parts = sorted(glob.glob(os.path.join(episode_dir, "*.mp3")), key=os.path.basename)
    return parts[max(1, episode.start_part) - 1:]


def _planned_copies(
    ready_episodes: List[Tuple[EpisodeRequest, str]]
) -> List[Tuple[EpisodeRequest, str, str]]:
    """(episode, source, device name) for every part to put on the player, in play order."""
    planned: List[Tuple[EpisodeRequest, str, str]] = []
    for episode, episode_dir in sorted(ready_episodes, key=lambda item: item[0].date):
        for source in _parts_to_copy(episode, episode_dir):
            planned.append((episode, source, device_name(os.path.basename(source))))
    return planned


def _mp3s_on_device(podcast_folder_path: str) -> Dict[str, int]:
    """The MP3s in the player's podcast folder, as name -> size."""
    return {
        os.path.basename(path): os.path.getsize(path)
        for path in glob.glob(os.path.join(podcast_folder_path, "*.mp3"))
    }


def _delete_mp3_files(podcast_folder_path: str) -> None:
    """Delete all MP3 files from the podcast folder."""
    mp3_pattern = os.path.join(podcast_folder_path, "*.mp3")
    mp3_files = glob.glob(mp3_pattern)
    for mp3_file in mp3_files:
        os.remove(mp3_file)
        print(f"[Podcast Sync] Deleted: {os.path.basename(mp3_file)}")


def sync_podcast_episodes_to_device() -> None:
    """Sync podcast episodes from library to device.

    Cheap players often play a folder in the order its files were written, so new
    parts mean wiping the folder and copying everything again in order. When the only
    change is parts to drop (heard parts, or an episode no longer picked), they
    are deleted and the rest stay as they are, in the same order.
    """
    device_sdcard_path = config.device_sd_path

    if not device_sdcard_path:
        raise RuntimeError("OPEN_SWIM_SD_PATH environment variable not set")

    if not os.path.exists(device_sdcard_path):
        raise RuntimeError(f"Device SD card path does not exist: {device_sdcard_path}")

    podcast_folder_path = os.path.join(device_sdcard_path, "podcast")
    if not os.path.exists(podcast_folder_path):
        raise RuntimeError(f"Podcast folder does not exist: {podcast_folder_path}")

    episodes_to_sync = load_episodes_to_sync()
    if not episodes_to_sync:
        print("[Podcast Sync] No episodes to sync")
        return

    library_info = store.load_library()
    ready_episodes = _episodes_ready_in_library(episodes_to_sync, library_info)
    planned = _planned_copies(ready_episodes)
    # Compare against what is actually ready, not what was requested: an episode
    # still downloading must not count as copied, or it never reaches the device.
    wanted = {name: os.path.getsize(source) for _, source, name in planned}
    on_device = _mp3s_on_device(podcast_folder_path)
    state = load_sync_state(device_sdcard_path)

    if wanted == on_device:
        print("[Podcast Sync] Episodes already up to date on device. Skipping.")
        return

    if wanted.items() <= on_device.items():
        for name in sorted(set(on_device) - set(wanted)):
            os.remove(os.path.join(podcast_folder_path, name))
            print(f"[Podcast Sync] Removed: {name}")
        state.podcasts.synced_episode_ids = [episode.id for episode, _ in ready_episodes]
        save_sync_state(state, device_sdcard_path)
        print("[Podcast Sync] Sync completed (parts removed, nothing copied)")
        return

    print("[Podcast Sync] Episode list changed. Syncing to device...")
    _delete_mp3_files(podcast_folder_path)

    failed_episode_ids = set()
    failures: List[str] = []
    for episode, source, filename in planned:
        destination_path = os.path.join(podcast_folder_path, filename)
        try:
            copy_file_to_device(source, destination_path)
            print(f"[Podcast Sync] Copied: {filename}")
        except Exception as e:
            # Carry on with the other segments and episodes.
            print(f"[Podcast Sync] Failed to copy '{filename}' for episode '{episode.id}': {e}")
            failures.append(f"'{filename}': {e}")
            failed_episode_ids.add(episode.id)

    # Record only fully copied episodes, so a failed one is copied again next sync.
    state.podcasts.synced_episode_ids = [
        episode.id for episode, _ in ready_episodes if episode.id not in failed_episode_ids
    ]
    save_sync_state(state, device_sdcard_path)

    if failures:
        raise RuntimeError(copy_failures_message("[Podcast Sync]", failures))
    print("[Podcast Sync] Sync completed")
