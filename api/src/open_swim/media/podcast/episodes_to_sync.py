import json

from open_swim.media.podcast.models import EpisodeRequest
from open_swim.media.podcast import store


def update_episodes_to_sync(json_payload: str) -> None:
    """Persist requested episodes to sync."""
    episodes = _convert_json_to_episode_list(json_payload)
    store.save_episode_requests(episodes)


def _convert_json_to_episode_list(json_payload: str) -> list[EpisodeRequest]:
    """Convert JSON string to a list of EpisodeRequest objects."""
    data = json.loads(json_payload)
    return [EpisodeRequest(**item) for item in data]


def load_episodes_to_sync() -> list[EpisodeRequest]:
    """Load the list of episodes to sync from a JSON file."""
    return store.load_episode_requests()
