import json
import os
from typing import List, Optional

from pydantic import BaseModel, Field

from open_swim.config import config


class DevicePlaylistState(BaseModel):
    """State for a playlist mirrored to the device."""

    id: str
    title: str
    playlist_hash: Optional[str] = None
    video_count: Optional[int] = None


class DevicePodcastState(BaseModel):
    """State for podcasts mirrored to the device."""

    synced_episode_ids: List[str] = Field(default_factory=list)


class DeviceSyncState(BaseModel):
    """Root device sync state persisted on the SD card."""

    schema_version: int = 1
    playlists: List[DevicePlaylistState] = Field(default_factory=list)
    podcasts: DevicePodcastState = Field(default_factory=DevicePodcastState)


def _state_path(sd_card_path: str) -> str:
    return os.path.join(sd_card_path, "sync_state.json")


def load_sync_state(sd_card_path: str | None = None) -> DeviceSyncState:
    """Load device sync state from SD card."""
    path = sd_card_path or config.device_sd_path
    sync_json_path = _state_path(path)
    if not os.path.exists(sync_json_path):
        return DeviceSyncState()
    with open(sync_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return DeviceSyncState(**data)


def save_sync_state(state: DeviceSyncState, sd_card_path: str | None = None) -> None:
    """Persist device sync state to SD card."""
    path = sd_card_path or config.device_sd_path
    os.makedirs(path, exist_ok=True)
    sync_json_path = _state_path(path)
    with open(sync_json_path, "w", encoding="utf-8") as f:
        json.dump(state.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"[Device Sync] Saved sync state to {sync_json_path}")
