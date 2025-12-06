import json

from open_swim.media.youtube.models import PlaylistRequest
from open_swim.media.youtube import store


def update_playlists_to_sync(json_payload: str) -> None:
    """Persist the requested playlists to sync."""
    playlists = _convert_json_to_playlist_list(json_payload)
    store.save_playlist_requests(playlists)


def _convert_json_to_playlist_list(json_payload: str) -> list[PlaylistRequest]:
    """Convert JSON string to a list of PlaylistRequest objects."""
    data = json.loads(json_payload)
    return [PlaylistRequest(**item) for item in data]


def load_playlists_to_sync() -> list[PlaylistRequest]:
    """Load the list of playlists to sync from a JSON file."""
    return store.load_playlist_requests()
