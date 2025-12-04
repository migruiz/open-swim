import os

from open_swim.config import config


def create_podcast_folder() -> None:
    """Get and validate the podcast directory path on the SD card."""
    sd_card_path = config.device_sd_path

    if not os.path.exists(sd_card_path):
        raise FileNotFoundError(f"SD card path does not exist: {sd_card_path}")

    if not os.access(sd_card_path, os.W_OK):
        raise PermissionError(f"SD card path is not writable: {sd_card_path}")

    podcast_path = os.path.join(sd_card_path, "podcast")
    os.makedirs(podcast_path, exist_ok=True)
