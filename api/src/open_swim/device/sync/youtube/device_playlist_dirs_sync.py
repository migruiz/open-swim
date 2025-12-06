import os
import json
import shutil
from typing import List, Dict, Any

from pydantic import BaseModel, Field

from open_swim.config import config
from open_swim.device.sync.youtube.sanitize import sanitize_playlist_title
from open_swim.media.youtube.playlists import PlaylistInfo


class DevicePlaylistEntry(BaseModel):
    """Playlist information saved on the device."""

    id: str
    title: str


class DeviceSyncInfo(BaseModel):
    """Current state of device sync information (stored on SD card)."""

    playlists: List[DevicePlaylistEntry] = Field(default_factory=list)


def sync_playlists_directories(playlists_to_sync: List[PlaylistInfo]) -> None:
    """Sync device information by loading and saving device_sync.json."""

    _prepare_device_directories(
        playlists_to_sync=playlists_to_sync
    )    


def _prepare_device_directories(
    playlists_to_sync: List[PlaylistInfo]
) -> None:
    """Ensure requested playlists have directories and remove ones no longer requested."""
    sd_card_path = config.device_sd_path
    device_info = _load_device_sync_info(sd_card_path)

    playlists_to_sync_by_id = {
        playlist.id: playlist for playlist in playlists_to_sync}
    existing_playlists_by_id = {
        playlist.id: playlist for playlist in device_info.playlists}

    # Remove any playlist folders that are no longer requested
    for playlist in device_info.playlists:
        if playlist.id in playlists_to_sync_by_id:
            continue
        sanitized_title = sanitize_playlist_title(playlist.title)
        playlist_path = os.path.join(sd_card_path, sanitized_title)
        if os.path.exists(playlist_path):
            shutil.rmtree(playlist_path)
            print(
                f"[Device Sync] Removed playlist folder no longer requested: {playlist_path}")

    # Ensure all requested playlists exist on device and update device info
    updated_playlists: List[DevicePlaylistEntry] = []
    for playlist in playlists_to_sync:
        sanitized_title = sanitize_playlist_title(playlist.title)
        playlist_path = os.path.join(sd_card_path, sanitized_title)

        if playlist.id not in existing_playlists_by_id and not os.path.exists(playlist_path):
            os.makedirs(playlist_path, exist_ok=True)
            print(f"[Device Sync] Created playlist folder: {playlist_path}")
        updated_playlists.append(
            DevicePlaylistEntry(
                id=playlist.id,
                title=sanitized_title,
            )
        )

    _save_device_sync_info(sd_card_path, DeviceSyncInfo(playlists=updated_playlists))


def _load_device_sync_info(sd_card_path: str) -> DeviceSyncInfo:
    """Load device_sync.json file if it exists."""
    sync_json_path = os.path.join(sd_card_path, "device_sync.json")
    if os.path.exists(sync_json_path):
        with open(sync_json_path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
            return DeviceSyncInfo(**data)
    return DeviceSyncInfo()


def _save_device_sync_info(sd_card_path: str, device_info: DeviceSyncInfo) -> None:
    """Save device sync data to device_sync.json file."""
    sync_json_path = os.path.join(sd_card_path, "device_sync.json")
    with open(sync_json_path, "w", encoding="utf-8") as f:
        json.dump(device_info.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"[Device Sync] Saved sync information to {sync_json_path}")
