import os
import secrets
import subprocess


def download_audio(video_id: str) -> str:
    """Download a YouTube video as an MP3 to a temp path and return the filepath."""
    if not video_id:
        raise ValueError("Video ID is required")

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    output_dir = "/tmp" if os.name != "nt" else os.environ.get("TEMP", ".")
    temp_filename = f"{secrets.token_hex(16)}.mp3"
    output_path = os.path.join(output_dir, temp_filename)

    yt_dlp_cmd = os.getenv("YTDLP_PATH", "yt-dlp")
    command = [
        yt_dlp_cmd,
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "-o",
        output_path,
        video_url,
    ]

    print(f"Downloading: {video_url}")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        _cleanup(output_path)
        raise RuntimeError("Download timeout") from exc

    if result.returncode != 0:
        print(f"yt-dlp error: {result.stderr}")
        _cleanup(output_path)
        raise RuntimeError(f"Failed to download video: {result.stderr}")

    if not os.path.exists(output_path):
        raise RuntimeError("Downloaded file not found")

    return output_path


def _cleanup(path: str) -> None:
    if os.path.exists(path):
        try:
            os.unlink(path)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            print(f"Failed to delete temp file {path}: {exc}")
