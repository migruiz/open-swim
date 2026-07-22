import os
import shutil
import hashlib
import time
from typing import List, Dict, Optional

from open_swim.config import config

# Maximum number of videos to sync per playlist (newest first)
PLAYLIST_SYNC_LIMIT = int(os.environ.get("PLAYLIST_SYNC_LIMIT", "20"))

from open_swim.device.sync.youtube.sanitize import sanitize_playlist_title
from open_swim.media.youtube.library import load_library
from open_swim.device.sync.state import DevicePlaylistState, load_sync_state, save_sync_state
from open_swim.media.youtube.models import YouTubeLibrary
from open_swim.media.youtube.playlists import PlaylistInfo, YoutubeVideo


def _reset_device_folder(path: str, attempts: int = 40, delay: float = 0.25) -> None:
    """Remove and recreate a folder, tolerating Windows' asynchronous directory
    deletion on removable drives.

    On Windows, ``shutil.rmtree`` can return while the directory is still in a
    "delete pending" state until the last handle is released. Recreating it
    immediately races that pending delete: ``os.makedirs`` may raise
    ``PermissionError`` (WinError 5), or succeed only for the pending delete to
    remove it moments later, leaving the following file copies to fail with
    ``FileNotFoundError`` (ENOENT). Poll until the delete settles, then create.
    """
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)

    # Wait for the asynchronous delete to actually complete before recreating.
    for _ in range(attempts):
        if not os.path.exists(path):
            break
        time.sleep(delay)

    # Recreate, retrying while Windows still reports the path as delete-pending.
    last_exc: Optional[Exception] = None
    for _ in range(attempts):
        try:
            os.makedirs(path, exist_ok=True)
            if os.path.isdir(path):
                return
        except OSError as exc:  # PermissionError / FileNotFoundError during pending delete
            last_exc = exc
        time.sleep(delay)

    raise RuntimeError(f"[Device Sync] Could not create folder '{path}': {last_exc}")


def _calculate_playlist_hash(videos: List[YoutubeVideo]) -> str:
    """Calculate a unique hash based on video IDs in the copy order."""
    video_data = "".join([f"{idx}:{video.id}" for idx, video in enumerate(videos)])
    return hashlib.sha256(video_data.encode()).hexdigest()


def _sync_playlist_to_device(
    playlist: PlaylistInfo,
    library_info: YouTubeLibrary,
    device_sdcard_path: str,
    sync_state: Dict[str, DevicePlaylistState],
    current_index: int,
    total_count: int,
) -> None:
    playlist_title = sanitize_playlist_title(playlist.title)
    playlist_folder_path = os.path.join(device_sdcard_path, playlist_title)
    videos_in_desc_order = list(reversed(playlist.videos))[:PLAYLIST_SYNC_LIMIT]

    # Calculate current playlist hash
    current_hash = _calculate_playlist_hash(videos_in_desc_order)

    stored_state = sync_state.get(playlist.id)
    if stored_state and stored_state.playlist_hash == current_hash:
        print(f"[Device Sync] Playlist {playlist.id} ({playlist.title}) is already up to date on device. Skipping.")
        return

    print(f"[Device Sync] Processing playlist: {playlist_title}")

    print(f"[Device Sync] Resetting folder: {playlist_folder_path}")
    _reset_device_folder(playlist_folder_path)
    print(f"[Device Sync] Created folder: {playlist_folder_path}")

    # Copy newest/last-added items first so files land on the device in descending order
    for video_index, video in enumerate(videos_in_desc_order, start=1):
        video_id = video.id

        if video_id not in library_info.videos:
            print(f"[Device Sync] Video {video_id} not found in library, skipping")
            continue

        video_info = library_info.videos[video_id]
        if not video_info.mp3_path:
            print(f"[Device Sync] No normalized MP3 for video {video_id} ({video.title}), skipping")
            continue
        if not os.path.exists(video_info.mp3_path):
            print(f"[Device Sync] Normalized MP3 file does not exist: {video_info.mp3_path}, skipping")
            continue

        filename = os.path.basename(video_info.mp3_path)
        destination_path = os.path.join(playlist_folder_path, filename)

        try:
            shutil.copy2(video_info.mp3_path, destination_path)
            print(f"[Device Sync] Copied: {filename} -> {playlist_title}/")
        except Exception as e:
            raise RuntimeError(
                f"[Device Sync] Failed to copy '{filename}' to playlist '{playlist_title}': {e}"
            ) from e

    print(f"[Device Sync] Completed playlist: {playlist_title}")

    sync_state[playlist.id] = DevicePlaylistState(
        id=playlist.id,
        title=playlist_title,
        playlist_hash=current_hash,
        video_count=len(videos_in_desc_order),
    )


def sync_device_playlists_videos(play_lists: List[PlaylistInfo]) -> None:
    """Sync the music library with the connected device."""
    library_info = load_library()
    device_sdcard_path = config.device_sd_path

    if not device_sdcard_path:
        raise RuntimeError("OPEN_SWIM_SD_PATH environment variable not set")

    if not os.path.exists(device_sdcard_path):
        raise RuntimeError(f"Device SD card path does not exist: {device_sdcard_path}")

    print(f"[Device Sync] Starting sync to device: {device_sdcard_path}")
    state = load_sync_state(device_sdcard_path)
    sync_state = {p.id: p for p in state.playlists}

    total_playlists = len(play_lists)
    for index, playlist in enumerate(play_lists, start=1):
        _sync_playlist_to_device(
            playlist,
            library_info,
            device_sdcard_path,
            sync_state,
            current_index=index,
            total_count=total_playlists,
        )

    state.playlists = list(sync_state.values())
    save_sync_state(state=state, sd_card_path=device_sdcard_path)

    print("[Device Sync] Sync completed")
