import json
import os
from pydantic import BaseModel
from typing import Dict

class VideoInfo(BaseModel):
    video_id: str
    path: str
    length: int
    name: str

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
        return None