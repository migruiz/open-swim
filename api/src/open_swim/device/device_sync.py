import os
import re
import shutil
import json
import hashlib
from typing import List, Dict, Any

from pydantic import BaseModel




class YoutubePlaylist(BaseModel):
    id: str
    title: str
    url: str = ""
    
class PodcastEpisode(BaseModel):
    id: str
    episode_dir: str


class DeviceSyncInfo(BaseModel):
    podcasts_dir_name: str = "podcasts"
    podcasts_episodes: List[PodcastEpisode] 
    playlists: List[YoutubePlaylist] 




def load_device_sync_info(sd_card_path: str) -> DeviceSyncInfo:
    """Load device_sync.json file if it exists."""
    sync_json_path = os.path.join(sd_card_path, "device_sync.json")
    if os.path.exists(sync_json_path):
        with open(sync_json_path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
            return DeviceSyncInfo(**data)
    return DeviceSyncInfo(podcasts_episodes=[], playlists=[])


def save_device_sync_info(sd_card_path: str, sync_data: DeviceSyncInfo) -> None:
    """Save device sync data to device_sync.json file."""
    sync_json_path = os.path.join(sd_card_path, "device_sync.json")
    with open(sync_json_path, "w", encoding="utf-8") as f:
        json.dump(sync_data.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"[Device Sync] Saved sync information to {sync_json_path}")

