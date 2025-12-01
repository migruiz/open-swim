import json
import os
import re
import shutil
from pydantic import BaseModel
from typing import Dict

from open_swim.youtube.playlist_extractor import YoutubeVideo

LIBRARY_PATH = os.getenv('LIBRARY_PATH', '/library')
youtube_library_path = os.path.join(LIBRARY_PATH, "youtube")

class LibraryMp3Info(BaseModel):
    video_id: str
    original_mp3_path: str
    original_mp3_downloaded: bool = False
    
    normalized_mp3_path: str | None = None
    normalized_mp3_converted: bool = False
    title: str


class LibraryData(BaseModel):
    videos: Dict[str, LibraryMp3Info]

    @classmethod
    def from_dict(cls, videos: dict) -> "LibraryData":
        """Parse the JSON structure where keys are video IDs"""
        return cls(videos=videos)


def get_library_video_info(video_id: str) -> LibraryMp3Info | None:
    library_data = load_library_info()
    return library_data.videos.get(video_id)


def load_library_info() -> LibraryData:
    info_json_path = os.path.join(youtube_library_path, "info.json")
    if os.path.exists(info_json_path):
        with open(info_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return LibraryData.from_dict(data["videos"])
    else:
        print("[Info JSON] info.json does not exist in /library/")
        return LibraryData(videos={})


def _save_original_file_to_library(temp_downloaded_mp3_path: str, youtube_video: YoutubeVideo) -> str:
    # Ensure /library/ directory exists
    os.makedirs(youtube_library_path, exist_ok=True)

    # Sanitize title to remove special characters
    sanitized_title = re.sub(r'[^\w\s-]', '', youtube_video.title)
    sanitized_title = re.sub(r'[\s]+', '_', sanitized_title.strip())
    
    # Create filename in format: [title]__original__[videoId].mp3
    filename = f"{sanitized_title}__original__{youtube_video.id}.mp3"
    destination_path = os.path.join(youtube_library_path, filename)
    
    # Copy the downloaded MP3 file to /library/
    shutil.copy2(temp_downloaded_mp3_path, destination_path)
    print(f"[File Copy] Original MP3 copied to {destination_path}")

    return destination_path


def _save_normalized_file_to_library(temp_normalized_mp3_path: str, youtube_video: YoutubeVideo) -> str:
    # Ensure /library/ directory exists
    os.makedirs(youtube_library_path, exist_ok=True)

    # Sanitize title to remove special characters
    sanitized_title = re.sub(r'[^\w\s-]', '', youtube_video.title)
    sanitized_title = re.sub(r'[\s]+', '_', sanitized_title.strip())
    
    # Create filename in format: [title]__normalized__[videoId].mp3
    filename = f"{sanitized_title}__normalized__{youtube_video.id}.mp3"
    destination_path = os.path.join(youtube_library_path, filename)
    
    # Copy the downloaded MP3 file to /library/
    shutil.copy2(temp_normalized_mp3_path, destination_path)
    print(f"[File Copy] Normalized MP3 copied to {destination_path}")
    return destination_path


def _save_library_info(library_data: LibraryData) -> None:
    info_json_path = os.path.join(youtube_library_path, "info.json")
    with open(info_json_path, "w", encoding="utf-8") as f:
        json.dump(library_data.model_dump(), f, indent=2)
    print(f"[Info JSON] Saved library info to {info_json_path}")


def add_original_mp3_to_library(youtube_video: YoutubeVideo, temp_downloaded_mp3_path: str) -> str:
    original_mp3_file_library_path = _save_original_file_to_library(
        temp_downloaded_mp3_path=temp_downloaded_mp3_path, youtube_video=youtube_video)
    
    video_info = LibraryMp3Info(
        video_id=youtube_video.id,
        title=youtube_video.title,
        original_mp3_path=original_mp3_file_library_path,
        original_mp3_downloaded=True
    )
    library_data = load_library_info()
    library_data.videos[youtube_video.id] = video_info
    _save_library_info(library_data)
    return original_mp3_file_library_path

def add_normalized_mp3_to_library(youtube_video: YoutubeVideo, temp_normalized_mp3_path: str) -> None:
    normalized_mp3_file_library_path = _save_normalized_file_to_library(
        temp_normalized_mp3_path=temp_normalized_mp3_path, youtube_video=youtube_video)
    video_info = get_library_video_info(youtube_video.id)
    assert video_info is not None, f"Video {youtube_video.id} must exist in library before adding normalized MP3"
    video_info.normalized_mp3_path = normalized_mp3_file_library_path
    video_info.normalized_mp3_converted = True
    library_data = load_library_info()
    library_data.videos[youtube_video.id] = video_info
    _save_library_info(library_data)