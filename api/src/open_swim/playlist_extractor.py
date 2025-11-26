import subprocess
import json
from typing import Dict, List, Any, Optional


def extract_playlist(playlist_url: str) -> Dict[str, Any]:
    """
    Extract playlist information from a YouTube playlist URL using yt-dlp.
    Raises ValueError or RuntimeError on error.
    Returns:
        Dict with 'videos': List of video information dictionaries
    """
    # Validate input
    if not playlist_url:
        raise ValueError("Playlist URL is required!")

    # Validate YouTube playlist URL
    is_valid_playlist = (
        'youtube.com' in playlist_url and 
        ('playlist?list=' in playlist_url or '&list=' in playlist_url)
    )

    if not is_valid_playlist:
        raise ValueError("Invalid YouTube playlist URL")

    try:
        # Execute yt-dlp command
        command = ['yt-dlp', '--flat-playlist', '--dump-json', playlist_url]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60
        )

        stdout = result.stdout
        stderr = result.stderr

        if stderr and not stdout:
            print(f'yt-dlp error: {stderr}')
            raise RuntimeError('Failed to fetch playlist information')

        # Parse JSON output (each line is a separate JSON object)
        videos: List[Dict[str, str]] = []

        for line in stdout.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

        
            data = json.loads(line)

            video_info = {
                'id': data.get('id', ''),
                'title': data.get('title', 'Unknown Title'),
                'url': data.get('url', f"https://www.youtube.com/watch?v={data.get('id', '')}"),
                'thumbnail': data.get('thumbnail', '') or (data.get('thumbnails', [{}])[0].get('url', '') if data.get('thumbnails') else ''),
                'duration': data.get('duration_string', 'Unknown')
            }

            videos.append(video_info)



        return {'videos': videos}

    except subprocess.TimeoutExpired:
        raise RuntimeError('Request timeout while fetching playlist')
    except Exception as e:
        print(f'Unexpected error: {e}')
        raise
