from typing import List
from open_swim.playlist_extractor import extract_playlist
from open_swim.mp3_downloader import download_mp3_to_temp
from open_swim.library_info import get_library_video_info, add_original_mp3_to_library, add_normalized_mp3_to_library
from open_swim.volume_normalizer import get_normalized_loudness_file


def sync_playlist(playlist_url: str) -> None:
    playlist_videos = extract_playlist(playlist_url)
    for video in playlist_videos:
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

        else:
            temp_downloaded_mp3_path = download_mp3_to_temp(
                video_id=video.id)
            original_mp3_path = add_original_mp3_to_library(
                youtube_video=video,
                temp_downloaded_mp3_path=temp_downloaded_mp3_path
            )
            temp_normalized_mp3_path = get_normalized_loudness_file(
                mp3_file_path=original_mp3_path
            )
            add_normalized_mp3_to_library(
                youtube_video=video,
                temp_normalized_mp3_path=temp_normalized_mp3_path
            )
    print(
        f"[Playlist] Extracted and processed {len(playlist_videos)} videos from playlist.")
