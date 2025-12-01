
import os
import secrets
import subprocess


def get_normalized_loudness_file(mp3_file_path: str) -> str:
    """
    A downloded MP3 file is normalized using ffmpeg's loudnorm filter to use in Open Swim  audio playback. bitrate is set to 128k. 
    The normalized file is saved in a temp directory and the path to the normalized file is returned.  
    use this logic for the temp temp file:
        # Set output directory
    output_dir = '/tmp' if os.name != 'nt' else os.environ.get('TEMP', '.')
        
    
    # Generate random temp filename
    temp_filename = f"{secrets.token_hex(16)}.mp3"
    output_path = os.path.join(output_dir, temp_filename)
    """
    # Set output directory
    output_dir = '/tmp' if os.name != 'nt' else os.environ.get('TEMP', '.')
    
    # Generate random temp filename
    temp_filename = f"{secrets.token_hex(16)}.mp3"
    output_path = os.path.join(output_dir, temp_filename)
    
    # Build ffmpeg command with loudnorm filter and 128k bitrate
    print(f"Normalizing loudness for file: {mp3_file_path}")
    ffmpeg_cmd = os.getenv('FFMPEG_PATH', 'ffmpeg')
    cmd = [
        ffmpeg_cmd,
        '-i', mp3_file_path,
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
        '-b:a', '128k',
        '-y',  # Overwrite output file if it exists
        output_path
    ]
    
    # Execute ffmpeg command
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    
    return output_path 


