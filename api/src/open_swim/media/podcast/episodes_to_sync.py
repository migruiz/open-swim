
from datetime import datetime
import os
from pydantic import BaseModel

class EpisodeToSync(BaseModel):
    id: str
    date: datetime
    download_url: str
    title: str

LIBRARY_PATH = os.getenv('LIBRARY_PATH', '/library')
podcasts_library_path = os.path.join(LIBRARY_PATH, "podcasts")
    
def _save_episodes_to_sync(episodes: list[EpisodeToSync]) -> None:
    """Save the list of episodes to sync to a JSON file."""
    import json
    os.makedirs(podcasts_library_path, exist_ok=True)
    library_file_path = os.path.join(podcasts_library_path, "episodes_to_sync.json")
    with open(library_file_path, "w", encoding="utf-8") as f:
        json.dump([episode.model_dump() for episode in episodes], f, default=str, indent=2)

def load_episodes_to_sync() -> list[EpisodeToSync]:
    """Load the list of episodes to sync from a JSON file."""
    import json
    library_file_path = os.path.join(podcasts_library_path, "episodes_to_sync.json")
    if os.path.exists(library_file_path):
        with open(library_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [EpisodeToSync(**item) for item in data]
    return []

def update_episodes_to_sync(json_payload: str) -> None:
    """Persist requested episodes to sync."""
    episodes = _convert_json_to_episode_list(json_payload)
    _save_episodes_to_sync(episodes)

def _convert_json_to_episode_list(json_payload: str) -> list[EpisodeToSync]:
    """Convert JSON string to a list of EpisodeToSync objects."""
    import json
    data = json.loads(json_payload)
    episode_list = [EpisodeToSync(**item) for item in data]
    return episode_list
