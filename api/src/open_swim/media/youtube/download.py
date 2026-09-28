import os
from pathlib import Path
import secrets
import subprocess

from open_swim.config import config
from open_swim.media.youtube.ytdlp import run_ytdlp


def download_audio(tmp_path: Path, video_id: str) -> str:
    """Download a YouTube video as an MP3 to a temp path and return the filepath."""
    if not video_id:
        raise ValueError("Video ID is required")

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    output_path = tmp_path / f"{secrets.token_hex(16)}.mp3"

    command = [
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "-o",
        str(output_path),
    ]

    if config.ytdlp_player_client:
        command += [
            "--extractor-args",
            f"youtube:player_client={config.ytdlp_player_client}",
        ]

    command.append(video_url)

    print(f"Downloading: {video_url}")

    try:
        result = run_ytdlp(command, timeout=300)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Download timeout") from exc

    if result.returncode != 0:
        print(f"yt-dlp error: {result.stderr}")
        raise RuntimeError(f"Failed to download video: {result.stderr}")

    if not os.path.exists(output_path):
        raise RuntimeError("Downloaded file not found")

    return str(output_path)


