

import os
import shutil
from typing import List
from open_swim.library_info import LibraryData
from open_swim.playlist_extractor import PlaylistInfo


def sync_with_device(library_info: LibraryData, play_lists: List[PlaylistInfo]) -> None:
    """Sync the music library with the connected device."""
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
        playlist_title = playlist.title
        playlist_folder_path = os.path.join(device_sdcard_path, playlist_title)
        
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
            if not video_info.normalized_mp3_path:
                print(f"[Device Sync] No normalized MP3 for video {video_id} ({video.title}), skipping")
                continue
            
            if not os.path.exists(video_info.normalized_mp3_path):
                print(f"[Device Sync] Normalized MP3 file does not exist: {video_info.normalized_mp3_path}, skipping")
                continue
            
            # Copy the file to the device playlist folder
            filename = os.path.basename(video_info.normalized_mp3_path)
            destination_path = os.path.join(playlist_folder_path, filename)
            
            try:
                shutil.copy2(video_info.normalized_mp3_path, destination_path)
                print(f"[Device Sync] Copied: {filename} -> {playlist_title}/")
            except Exception as e:
                print(f"[Device Sync] Error copying {filename}: {e}")
        
        print(f"[Device Sync] Completed playlist: {playlist_title}")
    
    print("[Device Sync] Sync completed")
