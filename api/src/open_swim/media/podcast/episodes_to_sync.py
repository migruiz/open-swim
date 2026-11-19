import json
from typing import Any, Dict, List

from open_swim.media.podcast.models import EpisodeRequest, EpisodeStatus, PodcastLibrary
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


def episodes_to_sync_response(
    episodes: List[EpisodeRequest], library: PodcastLibrary
) -> List[Dict[str, Any]]:
    """The saved picks for the app, each with its part count once it is split (else null)."""
    response: List[Dict[str, Any]] = []
    for episode in episodes:
        item = episode.model_dump(mode="json")
        record = library.episodes.get(episode.id)
        ready = record is not None and record.status == EpisodeStatus.READY
        item["part_count"] = record.segment_count if record is not None and ready else None
        response.append(item)
    return response
