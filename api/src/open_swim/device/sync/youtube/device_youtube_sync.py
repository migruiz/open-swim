import os
import shutil
import hashlib
import time
from typing import List, Dict, Optional, Tuple

from open_swim.config import config
from open_swim.device.sync.youtube.sanitize import sanitize_playlist_title
from open_swim.media.youtube.library import load_library
from open_swim.device.sync.state import DevicePlaylistState, load_sync_state, save_sync_state
from open_swim.media.youtube.models import YouTubeLibrary
from open_swim.media.youtube.playlists import PlaylistInfo, YoutubeVideo, videos_to_sync


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


def _videos_ready_in_library(
    videos: List[YoutubeVideo], library_info: YouTubeLibrary
) -> List[Tuple[YoutubeVideo, str]]:
    """Videos whose normalized MP3 is in the library, paired with its path.

    The device hash covers only these, so a video that finishes downloading after
    a device sync changes the hash and is copied next time, instead of the
    playlist being recorded as complete without it.
    """
    ready: List[Tuple[YoutubeVideo, str]] = []
    for video in videos:
        video_info = library_info.videos.get(video.id)
        if video_info is None:
            print(f"[Device Sync] Video {video.id} not found in library, skipping")
            continue
        if not video_info.mp3_path:
            print(f"[Device Sync] No normalized MP3 for video {video.id} ({video.title}), skipping")
            continue
        if not os.path.exists(video_info.mp3_path):
            print(f"[Device Sync] Normalized MP3 file does not exist: {video_info.mp3_path}, skipping")
            continue
        ready.append((video, video_info.mp3_path))
    return ready


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
    ready_videos = _videos_ready_in_library(videos_to_sync(playlist), library_info)

    # Calculate current playlist hash
    current_hash = _calculate_playlist_hash([video for video, _ in ready_videos])

    stored_state = sync_state.get(playlist.id)
    if stored_state and stored_state.playlist_hash == current_hash:
        print(f"[Device Sync] Playlist {playlist.id} ({playlist.title}) is already up to date on device. Skipping.")
        return

    print(f"[Device Sync] Processing playlist: {playlist_title}")

    print(f"[Device Sync] Resetting folder: {playlist_folder_path}")
    _reset_device_folder(playlist_folder_path)
    print(f"[Device Sync] Created folder: {playlist_folder_path}")

    # Copy newest/last-added items first so files land on the device in descending order
    for _, mp3_path in ready_videos:
        filename = os.path.basename(mp3_path)
        destination_path = os.path.join(playlist_folder_path, filename)

        try:
            shutil.copy2(mp3_path, destination_path)
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
        video_count=len(ready_videos),
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
