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


class StageStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    error = "error"


class SyncStage(BaseModel):
    name: str
    label: str
    status: StageStatus = StageStatus.pending
    error: Optional[str] = None


class SyncProgressMessage(BaseModel):
    stages: list[SyncStage] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
