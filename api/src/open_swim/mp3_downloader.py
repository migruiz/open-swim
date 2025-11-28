import subprocess
import os
import secrets
import re
import sys
from typing import Dict, Any
from pathlib import Path
from pydantic import BaseModel






def download_mp3_to_temp(video_id: str) -> str:
    """
    Download a YouTube video as MP3 using yt-dlp.
    
    Args:
        video_id: The YouTube video ID
        output_dir: Directory to save the MP3 file (default: /tmp on Linux/Mac, temp dir on Windows)
        
    Returns:
        DownloadedMP3 object containing file_path, title, video_id, and file_size
        
    Raises:
        ValueError: If video_id is empty
        RuntimeError: If download fails or file not found
    """
    if not video_id:
        raise ValueError("Video ID is required")
    
    # Construct video URL
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Set output directory
    output_dir = '/tmp' if os.name != 'nt' else os.environ.get('TEMP', '.')
        
    
    # Generate random temp filename
    temp_filename = f"{secrets.token_hex(16)}.mp3"
    output_path = os.path.join(output_dir, temp_filename)
    
    try:
        # Download and convert to MP3 using yt-dlp
        # Use environment variable if set, otherwise default to 'yt-dlp' in PATH
        yt_dlp_cmd = os.getenv('YTDLP_PATH', 'yt-dlp')
        command = [
            yt_dlp_cmd,
            '-x',
            '--audio-format', 'mp3',
            '--audio-quality', '0',
            '-o', output_path,
            video_url
        ]
        
        print(f"Downloading: {video_url}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode != 0:
            print(f"yt-dlp error: {result.stderr}")
            raise RuntimeError(f"Failed to download video: {result.stderr}")
        
        # Check if file exists
        if not os.path.exists(output_path):
            raise RuntimeError("Downloaded file not found")
        

  
        
        return output_path
        
    except subprocess.TimeoutExpired:
        # Clean up partial download if exists
        if os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except Exception as e:
                print(f"Failed to delete temp file: {e}")
        raise RuntimeError("Download timeout")
    
    except Exception as e:
        # Clean up on error
        if os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except Exception as cleanup_error:
                print(f"Failed to delete temp file: {cleanup_error}")
        raise


def cleanup_mp3_file(file_path: str) -> bool:
    """
    Clean up (delete) an MP3 file.
    
    Args:
        file_path: Full path to the file to delete
        
    Returns:
        True if successfully deleted, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            print(f"Cleaned up file: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Failed to delete file {file_path}: {e}")
        return False
