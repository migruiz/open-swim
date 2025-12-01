from pathlib import Path
import tempfile
from typing import  List

from open_swim.media.youtube.download import download_audio
from open_swim.media.youtube.library import (
    add_normalized_mp3_to_library,
    get_library_video_info,
)
from open_swim.media.youtube.normalize import get_normalized_loudness_file
from open_swim.media.youtube.playlists import PlaylistInfo, YoutubeVideo, fetch_playlist
from open_swim.media.youtube.playlists_to_sync import load_playlists_to_sync


def _get_playlists_to_sync() -> List[PlaylistInfo]:
    """Return a list of playlist URLs to sync from environment variable."""
    playlists_to_sync = load_playlists_to_sync()

    playlist_ids = [playlist.id.strip()
                    for playlist in playlists_to_sync]
    playlist_urls = [
        f"https://youtube.com/playlist?list={playlist_id}" for playlist_id in playlist_ids]
    return [fetch_playlist(url) for url in playlist_urls]


def _sync_video_to_library(video: YoutubeVideo) -> None:
    """Sync a single video to the library, downloading and normalizing if needed."""
    library_video_info = get_library_video_info(video.id)
    if library_video_info:
        print(
            f"[Library Info] Video {video.title} - {video.id} already in library.")
    else:
        print(f"[Library Sync] Processing video {video.title} - {video.id}...")
            # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            temp_downloaded_mp3_path = download_audio(tmp_path=tmp_path, video_id=video.id)
            temp_normalized_mp3_path = get_normalized_loudness_file(
                tmp_path=tmp_path,
                mp3_file_path=temp_downloaded_mp3_path
            )
            add_normalized_mp3_to_library(
                youtube_video=video,
                temp_normalized_mp3_path=temp_normalized_mp3_path
            )


def _sync_library_playlist(playlist_info: PlaylistInfo) -> None:
    for video in playlist_info.videos:
        try:
            _sync_video_to_library(video)
        except Exception as e:
            print(f"[Error] Failed to sync video {video.title} - {video.id}: {str(e)}")
    print(
        f"[Playlist] Extracted and processed {len(playlist_info.videos)} videos from playlist.")
    




def sync_youtube_playlists_to_library() -> None:
    """Sync all playlists specified in environment variable to the library."""
    playlists_to_sync = _get_playlists_to_sync()
    for playlist in playlists_to_sync:
        print(f"[Playlist Sync] Syncing playlist: {playlist.title}")
        _sync_library_playlist(playlist)


