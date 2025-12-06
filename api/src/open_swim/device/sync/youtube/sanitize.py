import re


def sanitize_playlist_title(title: str) -> str:
    """Sanitize playlist titles for filesystem usage."""
    sanitized = re.sub(r"[^\w\s-]", "", title)
    sanitized = re.sub(r"[\s]+", "_", sanitized.strip())
    return sanitized or "playlist"
