import os
import subprocess
import json
import sys
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class YoutubeVideo(BaseModel):
    id: str
    title: str
    url: str = ""


class PlaylistInfo(BaseModel):
    id: str
    title: str
    uploader: Optional[str] = None
    uploader_id: Optional[str] = None
    playlist_count: int = Field(default=0, alias="_playlist_count")
    videos: List[YoutubeVideo] = []


def extract_playlist(playlist_url: str) -> PlaylistInfo:
    """
    Extract playlist information from a YouTube playlist URL using yt-dlp.
    Raises ValueError or RuntimeError on error.
    Returns:
        PlaylistInfo object containing playlist metadata and list of videos
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
        yt_dlp_cmd = os.getenv('YTDLP_PATH', 'yt-dlp')
        print(f"Extracting playlist info from URL: {playlist_url}")
        # Use --dump-single-json to get playlist metadata (including title) and entries
        command = [yt_dlp_cmd, '--dump-single-json','--flat-playlist', playlist_url]

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

        # Parse JSON output - --dump-single-json returns a single JSON object
        data = json.loads(stdout.strip())
        
        # Extract video entries
        # Note: yt-dlp returns playlist entries in the order they appear on YouTube by default.
        # The 'entries' list should be ordered as on the playlist page, unless yt-dlp options change it.
        videos: List[YoutubeVideo] = []
        for entry in data.get('entries', []):
            if not entry:  # Skip None entries
                continue
            
            video = YoutubeVideo(
                id=entry.get('id', ''),
                title=entry.get('title', 'Unknown Title'),
                url=entry.get('url', f"https://www.youtube.com/watch?v={entry.get('id', '')}")
            )
            videos.append(video)

        # Create PlaylistInfo object
        playlist_info = PlaylistInfo(
            id=data.get('id', ''),
            title=data.get('title', 'Unknown Playlist'),
            uploader=data.get('uploader'),
            uploader_id=data.get('uploader_id'),
            _playlist_count=data.get('playlist_count', len(videos)),
            videos=videos
        )

        return playlist_info

    except subprocess.TimeoutExpired:
        raise RuntimeError('Request timeout while fetching playlist')
    except json.JSONDecodeError as e:
        print(f'Failed to parse JSON output: {e}')
        raise RuntimeError('Failed to parse playlist information')
    except Exception as e:
        print(f'Unexpected error: {e}')
        raise
