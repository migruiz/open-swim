import json
import os
import re
import shutil
from pydantic import BaseModel
from typing import Dict

from open_swim.playlist_extractor import YoutubeVideo

LIBRARY_PATH = os.getenv('LIBRARY_PATH', '/library/')


class LibraryMp3Info(BaseModel):
    video_id: str
    original_mp3_path: str
    original_mp3_downloaded: bool = False
    duration: int
    title: str


class LibraryData(BaseModel):
    videos: Dict[str, LibraryMp3Info]

    @classmethod
    def from_dict(cls, videos: dict) -> "LibraryData":
        """Parse the JSON structure where keys are video IDs"""
        return cls(videos=videos)


def is_video_in_library(video_id: str) -> bool:
    library_data = _load_library_info()
    return video_id in library_data.videos


def _load_library_info() -> LibraryData:
    info_json_path = os.path.join(LIBRARY_PATH, "info.json")
    if os.path.exists(info_json_path):
        with open(info_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return LibraryData.from_dict(data["videos"])
    else:
        print("[Info JSON] info.json does not exist in /library/")
        return LibraryData(videos={})


def _save_file_to_library(temp_downloaded_mp3_path: str, youtube_video: YoutubeVideo) -> str:
    # Ensure /library/ directory exists
    os.makedirs(LIBRARY_PATH, exist_ok=True)

    # Sanitize title to remove special characters
    sanitized_title = re.sub(r'[^\w\s-]', '', youtube_video.title)
    sanitized_title = re.sub(r'[\s]+', '_', sanitized_title.strip())
    
    # Create filename in format: [title]__original__[videoId].mp3
    filename = f"{sanitized_title}__original__{youtube_video.id}.mp3"
    destination_path = os.path.join(LIBRARY_PATH, filename)
    
    # Copy the downloaded MP3 file to /library/
    shutil.copy2(temp_downloaded_mp3_path, destination_path)
    print(f"[File Copy] Copied MP3 to {destination_path}")

    print(
        f"[MP3 Downloader] Downloaded MP3 for video ID {youtube_video.id}: {destination_path}")
    return destination_path


def _save_library_info(library_data: LibraryData) -> None:
    info_json_path = os.path.join(LIBRARY_PATH, "info.json")
    with open(info_json_path, "w", encoding="utf-8") as f:
        json.dump(library_data.model_dump(), f, indent=2)
    print(f"[Info JSON] Saved library info to {info_json_path}")


def add_original_mp3_to_library(youtube_video: YoutubeVideo, temp_downloaded_mp3_path: str) -> None:
    mp3_file_library_path = _save_file_to_library(
        temp_downloaded_mp3_path=temp_downloaded_mp3_path, youtube_video=youtube_video)
    video_info = LibraryMp3Info(
        video_id=youtube_video.id,
        duration=youtube_video.duration,
        title=youtube_video.title,
        original_mp3_path=mp3_file_library_path,
        original_mp3_downloaded=True
    )
    library_data = _load_library_info()
    library_data.videos[youtube_video.id] = video_info
    _save_library_info(library_data)
