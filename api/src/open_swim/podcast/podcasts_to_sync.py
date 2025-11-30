import os
from pydantic import BaseModel
from datetime import datetime

class PodcastToSync(BaseModel):
    id: str
    date: datetime
    download_url: str
    title: str
    
LIBRARY_PATH = os.getenv('LIBRARY_PATH', '/library')
podcasts_library_path = os.path.join(LIBRARY_PATH, "podcasts")
  
def set_podcasts_to_sync(jsonList: str) -> None:
    """Add a podcast to the sync list (implementation placeholder)"""
    podcasts = _convert_json_to_podcast_list(jsonList)
    _save_podcasts_to_sync(podcasts)

def _convert_json_to_podcast_list(jsonList: str) -> list[PodcastToSync]:
    """Convert JSON string to a list of PodcastToSync objects."""
    import json
    data = json.loads(jsonList)
    podcast_list = [PodcastToSync(**item) for item in data]
    return podcast_list



def _save_podcasts_to_sync(podcasts: list[PodcastToSync]) -> None:
    """Save the list of podcasts to sync to a JSON file."""
    import json
    os.makedirs(podcasts_library_path, exist_ok=True)
    library_file_path = os.path.join(podcasts_library_path, "podcasts_to_sync.json")
    with open(library_file_path, "w", encoding="utf-8") as f:
        json.dump([podcast.model_dump() for podcast in podcasts], f, default=str, indent=2)
