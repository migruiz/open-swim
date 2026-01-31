import subprocess

from open_swim.app import run
from open_swim.config import config


def print_ytdlp_version() -> None:
    """Print the yt-dlp version and path being used."""
    try:
        result = subprocess.run(
            [config.ytdlp_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version = result.stdout.strip() if result.returncode == 0 else "unknown"
        print(f"yt-dlp path: {config.ytdlp_path}")
        print(f"yt-dlp version: {version}")
    except Exception as e:
        print(f"Failed to get yt-dlp version: {e}")


def main() -> None:
    print_ytdlp_version()
    run()


if __name__ == "__main__":
    main()
