import os
from typing import List
from open_swim.playlist_extractor import extract_playlist
from open_swim.mp3_downloader import download_mp3_to_temp
from open_swim.library_info import get_library_video_info, add_original_mp3_to_library, add_normalized_mp3_to_library
from open_swim.volume_normalizer import get_normalized_loudness_file
from open_swim.file_tools import remove_file


def get_playlist_to_sync() -> List[str]:
    """Return a list of playlist URLs to sync from environment variable."""
    playlist_ids_str = os.getenv("PLAYLIST_IDS", "")
    if not playlist_ids_str:
        return []
    
    playlist_ids = [id.strip() for id in playlist_ids_str.split(",") if id.strip()]
    return [f"https://youtube.com/playlist?list={playlist_id}" for playlist_id in playlist_ids]

def sync_library_playlist(playlist_url: str) -> None:
    playlist_info = extract_playlist(playlist_url)
    for video in playlist_info.videos:
        library_video_info = get_library_video_info(video.id)
        if library_video_info:
            print(
                f"[Library Info] Video ID {video.id} already in library.")
            if (not library_video_info.normalized_mp3_converted):
                temp_normalized_mp3_path = get_normalized_loudness_file(
                    mp3_file_path=library_video_info.original_mp3_path
                )
                add_normalized_mp3_to_library(
                    youtube_video=video,
                    temp_normalized_mp3_path=temp_normalized_mp3_path
                )
                remove_file(temp_normalized_mp3_path)
        else:
            temp_downloaded_mp3_path = download_mp3_to_temp(
                video_id=video.id)
            original_mp3_path = add_original_mp3_to_library(
                youtube_video=video,
                temp_downloaded_mp3_path=temp_downloaded_mp3_path
            )
            remove_file(temp_downloaded_mp3_path)
            temp_normalized_mp3_path = get_normalized_loudness_file(
                mp3_file_path=original_mp3_path
            )
            add_normalized_mp3_to_library(
                youtube_video=video,
                temp_normalized_mp3_path=temp_normalized_mp3_path
            )
            remove_file(temp_normalized_mp3_path)
    print(
        f"[Playlist] Extracted and processed {len(playlist_info.videos)} videos from playlist.")
