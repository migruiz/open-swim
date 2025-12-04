import os
import json
import shutil
from typing import List, Dict, Any

from pydantic import BaseModel, Field

from open_swim.media.youtube.playlists import PlaylistInfo
from open_swim.device.device_youtube_sync import sync_device_playlists


class DeviceSyncInfo(BaseModel):
    """Has the current state of the device sync information.
    This is stored in device_sync.json on the device's SD card."""
    playlists: List[PlaylistInfo] = Field(default_factory=list)


def sync(playlists_to_sync: List[PlaylistInfo]) -> None:
    """Sync device information by loading and saving device_sync.json."""

    prepare_device_directories(
        playlists_to_sync=playlists_to_sync
    )
    sync_device_playlists(play_lists=playlists_to_sync)


def prepare_device_directories(
    playlists_to_sync: List[PlaylistInfo]
) -> None:
    """Ensure requested playlists have directories and remove ones no longer requested."""
    sd_card_path = os.getenv("OPEN_SWIM_SD_PATH", "/sdcard")
    device_info = _load_device_sync_info(sd_card_path)

    playlists_to_sync_by_id = {
        playlist.id: playlist for playlist in playlists_to_sync}
    existing_playlists_by_id = {
        playlist.id: playlist for playlist in device_info.playlists}

    # Remove any playlist folders that are no longer requested
    for playlist in device_info.playlists:
        if playlist.id in playlists_to_sync_by_id:
            continue
        playlist_path = os.path.join(sd_card_path, playlist.title)
        if os.path.exists(playlist_path):
            shutil.rmtree(playlist_path)
            print(
                f"[Device Sync] Removed playlist folder no longer requested: {playlist_path}")

    # Ensure all requested playlists exist on device and update device info
    updated_playlists: List[PlaylistInfo] = []
    for playlist in playlists_to_sync:
        if playlist.id not in existing_playlists_by_id:
            playlist_path = os.path.join(sd_card_path, playlist.title)
            os.makedirs(playlist_path, exist_ok=True)
            print(f"[Device Sync] Created playlist folder: {playlist_path}")
        updated_playlists.append(PlaylistInfo(
            id=playlist.id, title=playlist.title))

    _save_device_sync_info(sd_card_path, device_info)


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
