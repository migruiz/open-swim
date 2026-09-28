"""Centralized configuration for Open Swim.

All environment variables are resolved once at import time.
Import this module to access configuration values.

Usage:
    from open_swim.config import config

    # Access paths
    library_path = config.library_path
    youtube_library_path = config.youtube_library_path

    # Access external tool paths
    ffmpeg_cmd = config.ffmpeg_path
"""

import os
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

# Must run before the module-level `config` singleton is created at the bottom of
# this file: every field resolves its environment variable at instantiation time,
# so a load_dotenv() call in an entry point (app.py) happens too late to be seen.
load_dotenv()


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""

    pass


@dataclass(frozen=True)
class Config:
    """Immutable application configuration.

    All paths are resolved at instantiation time from environment variables.
    Derived paths (youtube_library_path, podcasts_library_path) are computed
    from the base library_path.
    """

    # Base paths
    library_path: str = field(
        default_factory=lambda: os.getenv("LIBRARY_PATH", "/library")
    )
    device_sd_path: str = field(
        default_factory=lambda: os.getenv("OPEN_SWIM_SD_PATH", "")
    )

    # External tools
    ffmpeg_path: str = field(
        default_factory=lambda: os.getenv("FFMPEG_PATH", "ffmpeg")
    )
    ytdlp_path: str = field(default_factory=lambda: os.getenv("YTDLP_PATH", "yt-dlp"))
    # Optional YouTube player client for yt-dlp (e.g. "mweb"). YouTube periodically
    # blocks the default client's format URLs with HTTP 403; overriding the client
    # works around it. Empty means "let yt-dlp choose".
    ytdlp_player_client: str = field(
        default_factory=lambda: os.getenv("YTDLP_PLAYER_CLIENT", "")
    )
    # Release channel yt-dlp updates to after a failed download ("stable",
    # "nightly"). Empty means a plain `yt-dlp -U`, which stays on the installed
    # channel. The Docker image sets this to match docker-entrypoint.sh.
    ytdlp_update_channel: str = field(
        default_factory=lambda: os.getenv("YTDLP_UPDATE_CHANNEL", "")
    )
    piper_cmd: str = field(default_factory=lambda: os.getenv("PIPER_CMD", "piper"))
    piper_voice_model_path: str = field(
        default_factory=lambda: os.getenv(
            "PIPER_VOICE_MODEL_PATH", "/voices/en_US-hfc_female-medium.onnx"
        )
    )

    # MQTT
    mqtt_broker_uri: Optional[str] = field(
        default_factory=lambda: os.getenv("MQTT_BROKER_URI")
    )

    # Sync behaviour
    # Newest N videos per playlist that are downloaded and copied to the device.
    playlist_sync_limit: int = field(
        default_factory=lambda: int(os.getenv("PLAYLIST_SYNC_LIMIT", "20"))
    )
    # Hours between automatic syncs; 0 disables them.
    sync_interval_hours: float = field(
        default_factory=lambda: float(os.getenv("SYNC_INTERVAL_HOURS", "2"))
    )
    # Quiet period after the last selection change before a sync starts, so
    # ticking episodes one by one does not start a download per tick.
    selection_sync_delay_seconds: float = field(
        default_factory=lambda: float(os.getenv("SELECTION_SYNC_DELAY_SECONDS", "120"))
    )
    # Delete library files that are no longer selected. Off by default so a
    # developer's local library is never touched; the Pi stack turns it on.
    library_prune: bool = field(
        default_factory=lambda: os.getenv("LIBRARY_PRUNE", "false").strip().lower()
        in ("1", "true", "yes", "on")
    )

    @property
    def youtube_library_path(self) -> str:
        """Path to YouTube library subdirectory."""
        return os.path.join(self.library_path, "youtube")

    @property
    def podcasts_library_path(self) -> str:
        """Path to podcasts library subdirectory."""
        return os.path.join(self.library_path, "podcasts")

    @property
    def temp_dir(self) -> str:
        """Cross-platform temporary directory."""
        if sys.platform != "win32":
            return "/tmp"
        return os.environ.get("TEMP", tempfile.gettempdir())

    def validate_required(self) -> None:
        """Validate that required configuration is present.

        Call this at application startup to fail fast on missing config.

        Raises:
            ConfigurationError: If required configuration is missing.
        """
        if not self.mqtt_broker_uri:
            raise ConfigurationError("MQTT_BROKER_URI is required but not set")

    def validate_device_path(self) -> None:
        """Validate device SD path is configured and accessible.

        Call this before device sync operations.

        Raises:
            ConfigurationError: If device path is not configured or doesn't exist.
        """
        if not self.device_sd_path:
            raise ConfigurationError(
                "OPEN_SWIM_SD_PATH environment variable not set. "
                "Set this to the device mount point."
            )

        if not os.path.exists(self.device_sd_path):
            raise ConfigurationError(
                f"Device SD card path does not exist: {self.device_sd_path}"
            )


# Module-level singleton instance - resolved once at import time
config = Config()
