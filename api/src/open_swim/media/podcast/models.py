from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class EpisodeStatus(str, Enum):
    """Lifecycle states for a podcast episode in the library."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    SEGMENTING = "segmenting"
    INTRO_ADDED = "intro_added"
    READY = "ready"
    ERROR = "error"


class EpisodeRequest(BaseModel):
    """A requested podcast episode to sync."""

    id: str
    date: datetime
    download_url: str
    title: str
    # The part the user has reached; parts before it are heard and left off
    # the player. Counts from 1, like the spoken "3 of 18" at the start of a part.
    start_part: int = 1


class EpisodeRecord(BaseModel):
    """Processed podcast episode stored in the library."""

    id: str
    title: str
    date: datetime
    status: EpisodeStatus = EpisodeStatus.PENDING
    episode_dir: Optional[str] = None
    segment_count: Optional[int] = None
    error_message: Optional[str] = None


class PodcastLibrary(BaseModel):
    """Persisted podcast library metadata."""

    schema_version: int = 1
    episodes: Dict[str, EpisodeRecord] = Field(default_factory=dict)
