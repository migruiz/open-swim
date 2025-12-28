import os
import shutil
import hashlib
from typing import List, Dict

from open_swim.config import config

# Maximum number of videos to sync per playlist (newest first)
PLAYLIST_SYNC_LIMIT = int(os.environ.get("PLAYLIST_SYNC_LIMIT", "20"))

from open_swim.device.sync.youtube.sanitize import sanitize_playlist_title
from open_swim.messaging.models import SyncItemStatus, SyncPhase, SyncProgressMessage
from open_swim.messaging.progress import get_progress_reporter
from open_swim.media.youtube.library import load_library
from open_swim.device.sync.state import DevicePlaylistState, load_sync_state, save_sync_state
from open_swim.media.youtube.models import YouTubeLibrary
from open_swim.media.youtube.playlists import PlaylistInfo, YoutubeVideo


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
    reporter = get_progress_reporter()
    playlist_title = sanitize_playlist_title(playlist.title)
    playlist_folder_path = os.path.join(device_sdcard_path, playlist_title)
    videos_in_desc_order = list(reversed(playlist.videos))[:PLAYLIST_SYNC_LIMIT]

    # Calculate current playlist hash
    current_hash = _calculate_playlist_hash(videos_in_desc_order)

    stored_state = sync_state.get(playlist.id)
    if stored_state and stored_state.playlist_hash == current_hash:
        print(f"[Device Sync] Playlist {playlist.id} ({playlist.title}) is already up to date on device. Skipping.")
        reporter.report_progress(
            SyncProgressMessage(
                phase=SyncPhase.device_youtube,
                status=SyncItemStatus.skipped,
                playlist_id=playlist.id,
                playlist_title=playlist.title,
                current_index=current_index,
                total_count=total_count,
            )
        )
        return

    print(f"[Device Sync] Processing playlist: {playlist_title}")
    reporter.report_progress(
        SyncProgressMessage(
            phase=SyncPhase.device_youtube,
            status=SyncItemStatus.started,
            playlist_id=playlist.id,
            playlist_title=playlist.title,
            current_index=current_index,
            total_count=total_count,
        )
    )

    if os.path.exists(playlist_folder_path):
        print(f"[Device Sync] Removing existing folder: {playlist_folder_path}")
        shutil.rmtree(playlist_folder_path)

    os.makedirs(playlist_folder_path, exist_ok=True)
    print(f"[Device Sync] Created folder: {playlist_folder_path}")

    # Copy newest/last-added items first so files land on the device in descending order
    total_videos = len(videos_in_desc_order)
    for video_index, video in enumerate(videos_in_desc_order, start=1):
        video_id = video.id

        if video_id not in library_info.videos:
            print(f"[Device Sync] Video {video_id} not found in library, skipping")
            reporter.report_progress(
                SyncProgressMessage(
                    phase=SyncPhase.device_youtube,
                    status=SyncItemStatus.skipped,
                    playlist_id=playlist.id,
                    playlist_title=playlist.title,
                    item_id=video_id,
                    item_title=video.title,
                    current_index=video_index,
                    total_count=total_videos,
                    error_message="video not found in library",
                )
            )
            continue

        video_info = library_info.videos[video_id]
        if not video_info.mp3_path:
            print(f"[Device Sync] No normalized MP3 for video {video_id} ({video.title}), skipping")
            reporter.report_progress(
                SyncProgressMessage(
                    phase=SyncPhase.device_youtube,
                    status=SyncItemStatus.skipped,
                    playlist_id=playlist.id,
                    playlist_title=playlist.title,
                    item_id=video_id,
                    item_title=video.title,
                    current_index=video_index,
                    total_count=total_videos,
                    error_message="no normalized mp3 path",
                )
            )
            continue
        if not os.path.exists(video_info.mp3_path):
            print(f"[Device Sync] Normalized MP3 file does not exist: {video_info.mp3_path}, skipping")
            reporter.report_progress(
                SyncProgressMessage(
                    phase=SyncPhase.device_youtube,
                    status=SyncItemStatus.skipped,
                    playlist_id=playlist.id,
                    playlist_title=playlist.title,
                    item_id=video_id,
                    item_title=video.title,
                    current_index=video_index,
                    total_count=total_videos,
                    error_message=f"mp3 missing: {video_info.mp3_path}",
                )
            )
            continue

        filename = os.path.basename(video_info.mp3_path)
        destination_path = os.path.join(playlist_folder_path, filename)

        try:
            reporter.report_progress(
                SyncProgressMessage(
                    phase=SyncPhase.device_youtube,
                    status=SyncItemStatus.copying,
                    playlist_id=playlist.id,
                    playlist_title=playlist.title,
                    item_id=video_id,
                    item_title=video.title,
                    current_index=video_index,
                    total_count=total_videos,
                )
            )
            shutil.copy2(video_info.mp3_path, destination_path)
            print(f"[Device Sync] Copied: {filename} -> {playlist_title}/")
        except Exception as e:
            reporter.report_progress(
                SyncProgressMessage(
                    phase=SyncPhase.device_youtube,
                    status=SyncItemStatus.error,
                    playlist_id=playlist.id,
                    playlist_title=playlist.title,
                    item_id=video_id,
                    item_title=video.title,
                    current_index=video_index,
                    total_count=total_videos,
                    error_message=str(e),
                )
            )
            raise RuntimeError(
                f"[Device Sync] Failed to copy '{filename}' to playlist '{playlist_title}': {e}"
            ) from e

    print(f"[Device Sync] Completed playlist: {playlist_title}")
    reporter.report_progress(
        SyncProgressMessage(
            phase=SyncPhase.device_youtube,
            status=SyncItemStatus.completed,
            playlist_id=playlist.id,
            playlist_title=playlist.title,
            current_index=current_index,
            total_count=total_count,
        )
    )

    sync_state[playlist.id] = DevicePlaylistState(
        id=playlist.id,
        title=playlist_title,
        playlist_hash=current_hash,
        video_count=len(videos_in_desc_order),
    )


def sync_device_playlists_videos(play_lists: List[PlaylistInfo]) -> None:
    """Sync the music library with the connected device."""
    reporter = get_progress_reporter()
    library_info = load_library()
    device_sdcard_path = config.device_sd_path

    if not device_sdcard_path:
        print("[Device Sync] OPEN_SWIM_SD_PATH environment variable not set")
        reporter.report_progress(
            SyncProgressMessage(
                phase=SyncPhase.device_youtube,
                status=SyncItemStatus.error,
                error_message="OPEN_SWIM_SD_PATH environment variable not set",
            )
        )
        return

    if not os.path.exists(device_sdcard_path):
        print(f"[Device Sync] Device SD card path does not exist: {device_sdcard_path}")
        reporter.report_progress(
            SyncProgressMessage(
                phase=SyncPhase.device_youtube,
                status=SyncItemStatus.error,
                error_message=f"device sd path does not exist: {device_sdcard_path}",
            )
        )
        return
    
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
