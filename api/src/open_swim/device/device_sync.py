from typing import List
from open_swim.device.youtube.device_youtube_sync import sync_device_playlists_videos
from open_swim.device.youtube.device_playlist_dirs_sync import sync_playlists_directories
from open_swim.media.youtube.playlists import PlaylistInfo

def sync_device(playlists_to_sync: List[PlaylistInfo])-> None:
    sync_playlists_directories(playlists_to_sync)
    sync_device_playlists_videos(play_lists=playlists_to_sync)