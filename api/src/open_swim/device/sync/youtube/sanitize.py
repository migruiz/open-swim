import re

from open_swim.device.sync.files import device_name


def sanitize_playlist_title(title: str) -> str:
    """Sanitize playlist titles into a plain-ASCII folder name for the player."""
    sanitized = re.sub(r"[^\w\s-]", "", device_name(title))
    sanitized = re.sub(r"[\s]+", "_", sanitized.strip())
    return sanitized or "playlist"
