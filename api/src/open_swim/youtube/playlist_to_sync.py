import os
from pydantic import BaseModel
from datetime import datetime

class PlaylistToSync(BaseModel):
    id: str    
    #playlist_url: str
    #title: str
    
LIBRARY_PATH = os.getenv('LIBRARY_PATH', '/library')
youtube_library_path = os.path.join(LIBRARY_PATH, "youtube")
  
def set_playlists_to_sync(jsonList: str) -> None:
    """Add a playlist to the sync list (implementation placeholder)"""
    playlists = _convert_json_to_playlist_list(jsonList)
    _save_playlists_to_sync(playlists)

def _convert_json_to_playlist_list(jsonList: str) -> list[PlaylistToSync]:
    """Convert JSON string to a list of PlaylistToSync objects."""
    import json
    data = json.loads(jsonList)
    playlist_list = [PlaylistToSync(**item) for item in data]
    return playlist_list


def _save_playlists_to_sync(playlists: list[PlaylistToSync]) -> None:
    """Save the list of playlists to sync to a JSON file."""
    import json
    os.makedirs(youtube_library_path, exist_ok=True)
    library_file_path = os.path.join(youtube_library_path, "playlists_to_sync.json")
    with open(library_file_path, "w", encoding="utf-8") as f:
        json.dump([playlist.model_dump() for playlist in playlists], f, default=str, indent=2)

def load_playlists_to_sync() -> list[PlaylistToSync]:
    """Load the list of playlists to sync from a JSON file."""
    import json
    library_file_path = os.path.join(youtube_library_path, "playlists_to_sync.json")
    if os.path.exists(library_file_path):
        with open(library_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [PlaylistToSync(**item) for item in data]
    return []