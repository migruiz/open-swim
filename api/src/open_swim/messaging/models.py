from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PlaylistInfoRequest(BaseModel):
    playlist_id: str


class PlaylistInfoVideoItem(BaseModel):
    id: str
    title: str


class PlaylistInfoResponse(BaseModel):
    success: bool
    playlist_id: Optional[str] = None
    title: Optional[str] = None
    videos: list[PlaylistInfoVideoItem] = Field(default_factory=list)
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SyncPhase(str, Enum):
    youtube_library = "youtube_library"
    podcast_library = "podcast_library"
    device_youtube = "device_youtube"
    device_podcast = "device_podcast"


class SyncItemStatus(str, Enum):
    started = "started"
    downloading = "downloading"
    normalizing = "normalizing"
    segmenting = "segmenting"
    copying = "copying"
    completed = "completed"
    skipped = "skipped"
    error = "error"


class SyncProgressMessage(BaseModel):
    phase: SyncPhase
    status: SyncItemStatus

    playlist_id: Optional[str] = None
    playlist_title: Optional[str] = None

    item_id: Optional[str] = None
    item_title: Optional[str] = None

    current_index: Optional[int] = None
    total_count: Optional[int] = None
    percentage: Optional[float] = None

    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
