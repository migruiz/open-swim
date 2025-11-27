import json
import os
import shutil
from pydantic import BaseModel
from typing import Dict

from open_swim.mp3_downloader import DownloadedMP3
from open_swim.playlist_extractor import PlaylistVideo

LIBRARY_PATH = os.getenv('LIBRARY_PATH', '/library/')

class VideoInfo(BaseModel):
    video_id: str
    path: str
    duration: int
    title: str

class LibraryData(BaseModel):
    videos: Dict[str, VideoInfo]
    
    @classmethod
    def from_dict(cls, videos: dict) -> "LibraryData":
        """Parse the JSON structure where keys are video IDs"""
        return cls(videos=videos)

def load_library_info() -> LibraryData:
    info_json_path = os.path.join(LIBRARY_PATH, "info.json")
    if os.path.exists(info_json_path):
        with open(info_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return LibraryData.from_dict(data["videos"])
    else:
        print("[Info JSON] info.json does not exist in /library/")
        return LibraryData(videos={})

def save_file_to_library(mp3_info: DownloadedMP3) -> str:
        # Ensure /library/ directory exists     
    os.makedirs(LIBRARY_PATH, exist_ok=True)

    # Copy the downloaded MP3 file to /library/
    destination_path = os.path.join(LIBRARY_PATH, os.path.basename(mp3_info.file_path))
    shutil.copy2(mp3_info.file_path, destination_path)
    print(f"[File Copy] Copied MP3 to {destination_path}")

    print(f"[MP3 Downloader] Downloaded MP3 for video ID {mp3_info.video_id}: {mp3_info.file_path}") 
    return destination_path

def add_mp3_to_library_info(library_data: LibraryData,youtube_video: PlaylistVideo, downloaded_mp3_info: DownloadedMP3, mp3_file_library_path: str) -> None:
    video_info = VideoInfo(
        video_id=downloaded_mp3_info.video_id,
        duration=youtube_video.duration,
        title=youtube_video.title,      
        path=mp3_file_library_path
    )
    library_data.videos[downloaded_mp3_info.video_id] = video_info
    info_json_path = os.path.join(LIBRARY_PATH, "info.json")
    with open(info_json_path, "w", encoding="utf-8") as f:
        json.dump(library_data.model_dump(), f, indent=2)
    print(f"[Info JSON] Saved library info to {info_json_path}")