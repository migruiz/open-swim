import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from open_swim.playlist_extractor import PlaylistInfo, extract_playlist
from open_swim.mp3_downloader import download_mp3_to_temp
from open_swim.library_info import get_library_video_info, add_original_mp3_to_library, add_normalized_mp3_to_library, LIBRARY_PATH
from open_swim.volume_normalizer import get_normalized_loudness_file
from open_swim.file_tools import remove_file


def calculate_playlist_hash(playlist_info: PlaylistInfo) -> str:
    """Calculate a unique hash based on video IDs in order."""
    # Create a string with video IDs and their index positions
    video_data = "".join([f"{idx}:{video.id}" for idx, video in enumerate(playlist_info.videos)])
    return hashlib.sha256(video_data.encode()).hexdigest()


def load_sync_info() -> Dict[str, Any]:
    """Load sync.json file if it exists."""
    sync_json_path = os.path.join(LIBRARY_PATH, "sync.json")
    if os.path.exists(sync_json_path):
        with open(sync_json_path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
            return data
    return {}


def save_sync_info(sync_data: Dict[str, Any]) -> None:
    """Save sync data to sync.json file."""
    sync_json_path = os.path.join(LIBRARY_PATH, "sync.json")
    with open(sync_json_path, "w", encoding="utf-8") as f:
        json.dump(sync_data, f, indent=2, ensure_ascii=False)
    print(f"[Sync] Saved sync information to {sync_json_path}")


def get_playlist_to_sync() -> List[PlaylistInfo]:
    """Return a list of playlist URLs to sync from environment variable."""
    playlist_ids_str = os.getenv("PLAYLIST_IDS", "")
    if not playlist_ids_str:
        return []
    
    playlist_ids = [id.strip() for id in playlist_ids_str.split(",") if id.strip()]
    playlist_urls = [f"https://youtube.com/playlist?list={playlist_id}" for playlist_id in playlist_ids]
    return [extract_playlist(url) for url in playlist_urls]

def sync_library_playlist(playlist_info: PlaylistInfo) -> None:
    # Load existing sync info
    sync_data = load_sync_info()
    
    # Calculate current playlist hash
    current_hash = calculate_playlist_hash(playlist_info)
    
    # Check if playlist has already been synced with the same content
    playlist_key = f"playlist_{playlist_info.id}"
    if playlist_key in sync_data:
        stored_hash = sync_data[playlist_key].get("playlist_hash")
        if stored_hash == current_hash:
            print(f"[Sync] Playlist {playlist_info.id} ({playlist_info.title}) is already up to date. Skipping.")
            return
        else:
            print(f"[Sync] Playlist {playlist_info.id} has changed. Syncing updates...")
    else:
        print(f"[Sync] New playlist {playlist_info.id} ({playlist_info.title}). Starting sync...")
    
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
    
    # Update sync.json with current playlist info and hash
    sync_data[playlist_key] = {
        "playlist_id": playlist_info.id,
        "playlist_title": playlist_info.title,
        "playlist_hash": current_hash,
        "video_count": len(playlist_info.videos),
        "uploader": playlist_info.uploader,
        "uploader_id": playlist_info.uploader_id
    }
    save_sync_info(sync_data)
