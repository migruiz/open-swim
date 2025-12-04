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
