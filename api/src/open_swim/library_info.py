import json
import os
import shutil
from pydantic import BaseModel
from typing import Dict

from open_swim.mp3_downloader import DownloadedMP3

class VideoInfo(BaseModel):
    video_id: str
    path: str
    file_size: int
    title: str

class LibraryData(BaseModel):
    videos: Dict[str, VideoInfo]
    
    @classmethod
    def from_dict(cls, data: dict):
        """Parse the JSON structure where keys are video IDs"""
        return cls(videos=data)

def load_library_info():
    info_json_path = os.path.join("/library/", "info.json")
    if os.path.exists(info_json_path):
        with open(info_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return LibraryData.from_dict(data)
    else:
        print("[Info JSON] info.json does not exist in /library/")
        return LibraryData(videos={})

def save_file_to_library(mp3_info: DownloadedMP3):
        # Ensure /library/ directory exists 
    library_dir = "/library/"
    os.makedirs(library_dir, exist_ok=True)

    # Copy the downloaded MP3 file to /library/
    destination_path = os.path.join(library_dir, os.path.basename(mp3_info.file_path))
    shutil.copy2(mp3_info.file_path, destination_path)
    print(f"[File Copy] Copied MP3 to {destination_path}")

    print(f"[MP3 Downloader] Downloaded MP3 for video ID {mp3_info.video_id}: {mp3_info.file_path}") 
    return destination_path

def add_mp3_to_library_info(library_data: LibraryData, downloaded_mp3_info: DownloadedMP3, mp3_file_library_path: str):
    video_info = VideoInfo(
        video_id=downloaded_mp3_info.video_id,
        file_size=downloaded_mp3_info.file_size,
        title=downloaded_mp3_info.title,      
        path=mp3_file_library_path
    )
    library_data.videos[downloaded_mp3_info.video_id] = video_info
    info_json_path = os.path.join("/library/", "info.json")
    with open(info_json_path, "w", encoding="utf-8") as f:
        json.dump(library_data.model_dump(), f, indent=2)
    print(f"[Info JSON] Saved library info to {info_json_path}")