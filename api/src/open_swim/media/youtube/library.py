import os
import re
import shutil
from typing import Optional

from open_swim.config import config
from open_swim.media.youtube import store
from open_swim.media.youtube.models import VideoRecord, VideoStatus, YouTubeLibrary
from open_swim.media.youtube.playlists import YoutubeVideo


def load_library() -> YouTubeLibrary:
    """Load the YouTube library metadata."""
    return store.load_library()


def save_library(library: YouTubeLibrary) -> None:
    """Persist the YouTube library metadata."""
    store.save_library(library)


def get_library_video_info(video_id: str) -> Optional[VideoRecord]:
    """Return a stored video record if present."""
    library_data = load_library()
    return library_data.videos.get(video_id)


def _save_normalized_file_to_library(temp_normalized_mp3_path: str, youtube_video: YoutubeVideo) -> str:
    """Copy the normalized MP3 into the library with a sanitized filename."""
    os.makedirs(config.youtube_library_path, exist_ok=True)

    sanitized_title = re.sub(r"[^\w\s-]", "", youtube_video.title)
    sanitized_title = re.sub(r"[\s]+", "_", sanitized_title.strip())

    filename = f"{sanitized_title}__normalized__{youtube_video.id}.mp3"
    destination_path = os.path.join(config.youtube_library_path, filename)

    shutil.copy2(temp_normalized_mp3_path, destination_path)
    print(f"[File Copy] Normalized MP3 copied to {destination_path}")
    return destination_path


def add_normalized_mp3_to_library(
    youtube_video: YoutubeVideo,
    temp_normalized_mp3_path: str,
    playlist_id: str | None = None,
) -> VideoRecord:
    """Store a normalized MP3 and update the library record."""
    normalized_mp3_file_library_path = _save_normalized_file_to_library(
        temp_normalized_mp3_path=temp_normalized_mp3_path, youtube_video=youtube_video
    )

    library_data = load_library()
    existing = library_data.videos.get(youtube_video.id)

    record = VideoRecord(
        id=youtube_video.id,
        title=youtube_video.title,
        mp3_path=normalized_mp3_file_library_path,
        status=VideoStatus.READY,
        playlist_ids=existing.playlist_ids if existing else [],
    )
    if playlist_id and playlist_id not in record.playlist_ids:
        record.playlist_ids.append(playlist_id)

    library_data.videos[youtube_video.id] = record
    save_library(library_data)
    return record


def update_video_status(video_id: str, status: VideoStatus, error_message: str | None = None) -> None:
    """Update status for a video in the library."""
    library_data = load_library()
    record = library_data.videos.get(video_id)
    if record is None:
        record = VideoRecord(id=video_id, title="", status=status, error_message=error_message)
    else:
        record.status = status
        record.error_message = error_message
    library_data.videos[video_id] = record
    save_library(library_data)
