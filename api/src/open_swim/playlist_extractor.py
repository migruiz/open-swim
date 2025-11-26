import subprocess
import json
from typing import Dict, List, Any, Optional


def extract_playlist(playlist_url: str) -> Dict[str, Any]:
    """
    Extract playlist information from a YouTube playlist URL using yt-dlp.
    
    Args:
        playlist_url: The YouTube playlist URL
        
    Returns:
        Dict containing either:
        - 'videos': List of video information dictionaries
        - 'error': Error message with 'status' code
    """
    # Validate input
    if not playlist_url:
        return {
            'error': 'Playlist URL is required',
            'status': 400
        }
    
    # Validate YouTube playlist URL
    is_valid_playlist = (
        'youtube.com' in playlist_url and 
        ('playlist?list=' in playlist_url or '&list=' in playlist_url)
    )
    
    if not is_valid_playlist:
        return {
            'error': 'Invalid YouTube playlist URL',
            'status': 400
        }
    
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
            return {
                'error': 'Failed to fetch playlist information',
                'status': 500
            }
        
        # Parse JSON output (each line is a separate JSON object)
        videos: List[Dict[str, str]] = []
        
        for line in stdout.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            try:
                data = json.loads(line)
                
                video_info = {
                    'id': data.get('id', ''),
                    'title': data.get('title', 'Unknown Title'),
                    'url': data.get('url', f"https://www.youtube.com/watch?v={data.get('id', '')}"),
                    'thumbnail': data.get('thumbnail', '') or (data.get('thumbnails', [{}])[0].get('url', '') if data.get('thumbnails') else ''),
                    'duration': data.get('duration_string', 'Unknown')
                }
                
                videos.append(video_info)
                
            except json.JSONDecodeError as e:
                print(f'Failed to parse video data: {e}')
                continue
        
        return {'videos': videos}
        
    except subprocess.TimeoutExpired:
        return {
            'error': 'Request timeout while fetching playlist',
            'status': 500
        }
    except Exception as e:
        print(f'Unexpected error: {e}')
        return {
            'error': f'An unexpected error occurred: {str(e)}',
            'status': 500
        }
