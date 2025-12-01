import os
import re
import shutil
import json
import hashlib
from typing import List, Dict, Any

from open_swim.media.youtube.library import LibraryData, load_library_info
from open_swim.media.youtube.playlists import PlaylistInfo


def _calculate_playlist_hash(playlist: PlaylistInfo) -> str:
    """Calculate a unique hash based on video IDs in order."""
    # Create a string with video IDs and their index positions
    video_data = "".join([f"{idx}:{video.id}" for idx, video in enumerate(playlist.videos)])
    return hashlib.sha256(video_data.encode()).hexdigest()


def _load_device_sync_info(playlist_folder_path: str) -> Dict[str, Any]:
    """Load device_sync.json file if it exists."""
    sync_json_path = os.path.join(playlist_folder_path, "sync.json")
    if os.path.exists(sync_json_path):
        with open(sync_json_path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
            return data
    return {}


def _save_device_sync_info(playlist_folder_path: str, sync_data: Dict[str, Any]) -> None:
    """Save device sync data to device_sync.json file."""
    sync_json_path = os.path.join(playlist_folder_path, "sync.json")
    with open(sync_json_path, "w", encoding="utf-8") as f:
        json.dump(sync_data, f, indent=2, ensure_ascii=False)
    print(f"[Device Sync] Saved sync information to {sync_json_path}")


def _sync_playlist_to_device(playlist: PlaylistInfo, library_info: LibraryData, device_sdcard_path: str) -> None:
    
        # Sanitize playlist title to remove special characters
        playlist_title = re.sub(r'[<>:"/\\|?*]', '_', playlist.title)
        playlist_title = playlist_title.strip()
        playlist_folder_path = os.path.join(device_sdcard_path, playlist_title)
    
        # Load existing device sync info
        sync_data = _load_device_sync_info(playlist_folder_path)
        
        # Calculate current playlist hash
        current_hash = _calculate_playlist_hash(playlist)
        
        # Check if playlist has already been synced with the same content
        playlist_key = f"playlist_{playlist.id}"
        if playlist_key in sync_data:
            stored_hash = sync_data[playlist_key].get("playlist_hash")
            if stored_hash == current_hash:
                print(f"[Device Sync] Playlist {playlist.id} ({playlist.title}) is already up to date on device. Skipping.")
                return
            else:
                print(f"[Device Sync] Playlist {playlist.id} has changed. Syncing updates to device...")
        else:
            print(f"[Device Sync] New playlist {playlist.id} ({playlist.title}). Starting device sync...")
        

        
        print(f"[Device Sync] Processing playlist: {playlist_title}")
        
        # If the folder exists, remove it completely
        if os.path.exists(playlist_folder_path):
            print(f"[Device Sync] Removing existing folder: {playlist_folder_path}")
            shutil.rmtree(playlist_folder_path)
        
        # Create the playlist folder
        os.makedirs(playlist_folder_path, exist_ok=True)
        print(f"[Device Sync] Created folder: {playlist_folder_path}")
        
        # Iterate through each video in the playlist
        for video in playlist.videos:
            video_id = video.id
            
            # Get the video info from library
            if video_id not in library_info.videos:
                print(f"[Device Sync] Video {video_id} not found in library, skipping")
                continue
            
            video_info = library_info.videos[video_id]
            
            # Check if normalized mp3 exists
            if not video_info.mp3_path:
                print(f"[Device Sync] No normalized MP3 for video {video_id} ({video.title}), skipping")
                continue
            
            if not os.path.exists(video_info.mp3_path):
                print(f"[Device Sync] Normalized MP3 file does not exist: {video_info.mp3_path}, skipping")
                continue
            
            # Copy the file to the device playlist folder
            filename = os.path.basename(video_info.mp3_path)
            destination_path = os.path.join(playlist_folder_path, filename)
            
            try:
                shutil.copy2(video_info.mp3_path, destination_path)
                print(f"[Device Sync] Copied: {filename} -> {playlist_title}/")
            except Exception as e:
                print(f"[Device Sync] Error copying {filename}: {e}")
        
        print(f"[Device Sync] Completed playlist: {playlist_title}")
        
        # Update device_sync.json with current playlist info and hash
        sync_data[playlist_key] = {
            "playlist_id": playlist.id,
            "playlist_title": playlist.title,
            "playlist_hash": current_hash,
            "video_count": len(playlist.videos),
            "uploader": playlist.uploader,
            "uploader_id": playlist.uploader_id
        }
        _save_device_sync_info(playlist_folder_path = playlist_folder_path, sync_data = sync_data)


def sync_device_playlists(play_lists: List[PlaylistInfo]) -> None:
    """Sync the music library with the connected device."""
    library_info = load_library_info()
    device_sdcard_path = os.getenv('OPEN_SWIM_SD_PATH', '')
    
    if not device_sdcard_path:
        print("[Device Sync] OPEN_SWIM_SD_PATH environment variable not set")
        return
    
    if not os.path.exists(device_sdcard_path):
        print(f"[Device Sync] Device SD card path does not exist: {device_sdcard_path}")
        return
    
    print(f"[Device Sync] Starting sync to device: {device_sdcard_path}")
    
    # Iterate through each playlist
    for playlist in play_lists:
        _sync_playlist_to_device(playlist, library_info, device_sdcard_path)

    
    print("[Device Sync] Sync completed")
