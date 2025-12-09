import os
import shutil
from typing import List

from open_swim.config import config
from open_swim.device.sync.state import DevicePlaylistState, load_sync_state, save_sync_state
from open_swim.device.sync.youtube.sanitize import sanitize_playlist_title
from open_swim.media.youtube.playlists import PlaylistInfo


def sync_playlists_directories(playlists_to_sync: List[PlaylistInfo]) -> None:
    """Ensure playlist directories exist on device and remove stale ones."""
    _prepare_device_directories(playlists_to_sync=playlists_to_sync)


def _prepare_device_directories(playlists_to_sync: List[PlaylistInfo]) -> None:
    """Ensure requested playlists have directories and remove ones no longer requested."""
    sd_card_path = config.device_sd_path
    state = load_sync_state(sd_card_path)

    playlists_to_sync_by_id = {playlist.id: playlist for playlist in playlists_to_sync}
    existing_playlists_by_id = {playlist.id: playlist for playlist in state.playlists}

    # Remove any playlist folders that are no longer requested
    for existing_playlist in list(state.playlists):
        if existing_playlist.id in playlists_to_sync_by_id:
            continue
        playlist_path = os.path.join(sd_card_path, existing_playlist.title)
        if os.path.exists(playlist_path):
            shutil.rmtree(playlist_path)
            print(f"[Device Sync] Removed playlist folder no longer requested: {playlist_path}")

    updated_playlists: List[DevicePlaylistState] = []
    for playlist in playlists_to_sync:  # type: PlaylistInfo
        sanitized_title = sanitize_playlist_title(playlist.title)
        playlist_path = os.path.join(sd_card_path, sanitized_title)

        if playlist.id not in existing_playlists_by_id and not os.path.exists(playlist_path):
            os.makedirs(playlist_path, exist_ok=True)
            print(f"[Device Sync] Created playlist folder: {playlist_path}")

        existing = existing_playlists_by_id.get(playlist.id)
        if existing and existing.title != sanitized_title:
            old_path = os.path.join(sd_card_path, existing.title)
            if os.path.exists(old_path):
                shutil.rmtree(old_path)
                print(f"[Device Sync] Removed renamed playlist folder: {old_path}")

        updated_playlists.append(
            DevicePlaylistState(
                id=playlist.id,
                title=sanitized_title,
                playlist_hash=getattr(existing, "playlist_hash", None),
                video_count=getattr(existing, "video_count", None),
            )
        )

    state.playlists = updated_playlists
    save_sync_state(state, sd_card_path)
