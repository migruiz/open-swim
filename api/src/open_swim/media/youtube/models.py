from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class VideoStatus(str, Enum):
    """Lifecycle states for a YouTube item in the library."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    NORMALIZING = "normalizing"
    ADDING_INTRO = "adding_intro"
    READY = "ready"
    ERROR = "error"


class PlaylistRequest(BaseModel):
    """A requested playlist to sync."""

    id: str
    title: str


class VideoRecord(BaseModel):
    """Normalized YouTube track stored in the library."""

    id: str
    title: str
    status: VideoStatus = VideoStatus.PENDING
    mp3_path: Optional[str] = None
    playlist_ids: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class YouTubeLibrary(BaseModel):
    """Persisted YouTube library metadata."""

    schema_version: int = 1
    videos: Dict[str, VideoRecord] = Field(default_factory=dict)
