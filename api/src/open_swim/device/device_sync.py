import os
import json
from typing import List, Dict, Any

from pydantic import BaseModel

from open_swim.media.youtube.playlists_to_sync import PlaylistToSync, load_playlists_to_sync


class PlayListInfo(BaseModel):
    id: str
    title: str



class DeviceSyncInfo(BaseModel):
    """Has the current state of the device sync information.
    This is stored in device_sync.json on the device's SD card."""
    podcasts_dir: str = "podcasts"
    playlists: List[PlayListInfo] 


def sync() -> None:
    """Sync device information by loading and saving device_sync.json."""
    sd_card_path = os.getenv("OPEN_SWIM_SD_PATH", "/sdcard")
    device_info = _load_device_sync_info(sd_card_path)
    
    # Load the playlists to sync from the main library
    playlists_to_sync = load_playlists_to_sync()
    
    # Here you would add logic to update device_info as needed
    # based on the device_info and playlists_to_sync. Remove the playlist directory on the device if it's no longer in playlists_to_sync. The playlist directory is assumed to be the title of the playlist. 
    # if a playlist is in playlists_to_sync but not in device_info, add it. Just create a folder with the title of the playlist.
    _save_device_sync_info(sd_card_path, device_info)


def _load_device_sync_info(sd_card_path: str) -> DeviceSyncInfo:
    """Load device_sync.json file if it exists."""
    sync_json_path = os.path.join(sd_card_path, "device_sync.json")
    if os.path.exists(sync_json_path):
        with open(sync_json_path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
            return DeviceSyncInfo(**data)
    return DeviceSyncInfo(playlists_titles=[])


def _save_device_sync_info(sd_card_path: str, device_info: DeviceSyncInfo) -> None:
    """Save device sync data to device_sync.json file."""
    sync_json_path = os.path.join(sd_card_path, "device_sync.json")
    with open(sync_json_path, "w", encoding="utf-8") as f:
        json.dump(device_info.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"[Device Sync] Saved sync information to {sync_json_path}")

