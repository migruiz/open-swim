

from typing import List
import os
import tempfile
import subprocess
from pathlib import Path
import requests
from open_swim.podcast.episodes_to_sync import EpisodeToSync, load_episodes_to_sync


def sync_podcast_episodes() -> None:
    """Sync multiple podcast episodes by processing each one."""
    episodes = load_episodes_to_sync()
    for episode in episodes:
        process_podcast_episode(
            episode=episode, episode_number=episodes.index(episode) + 1)


def process_podcast_episode(episode: EpisodeToSync, episode_number: int) -> None:
    """Process a podcast episode by downloading, splitting, adding intros, and merging segments."""
    # Create a temporary directory for processing
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Download the podcast
        print(f"Downloading podcast from {episode.download_url}...")
        episode_path = download_podcast(
            url=episode.download_url, output_dir=tmp_path)

        # 2. Split the podcast into 10-minute segments
        print("Splitting podcast into 10-minute segments...")
        segment_paths = split_podcast_episode(
            episode_path=episode_path, output_dir=tmp_path)

        # 3 & 4. For each segment, generate intro and merge
        total_segments = len(segment_paths)
        print(f"Processing {total_segments} segments...")
        final_segments = []
        for index, segment_path in enumerate(segment_paths, start=1):
            print(f"Processing segment {index} of {total_segments}...")

            # Generate audio intro
            intro_path = generate_audio_intro(
                episode_number=episode_number, index=index, total=total_segments, output_dir=tmp_path)

            # Merge intro and segment
            merged_path = merge_intro_and_segment(
                segment_path, intro_path, tmp_path, index)
            final_segments.append(merged_path)

        print(
            f"Processing complete! Generated {len(final_segments)} segments.")
        # Note: Files are in tmp_dir and will be cleaned up automatically
        # If you need to save them permanently, copy them before this function ends


def download_podcast(url: str, output_dir: Path) -> Path:
    """Download podcast from the given URL.
    Returns the path to the downloaded file."""

    response = requests.get(url, stream=True)
    response.raise_for_status()

    # Generate filename from URL or use a default
    filename = (url.split('/')[-1] or 'podcast.mp3')[:18]
    if not filename.endswith('.mp3'):
        filename += '.mp3'

    output_path = output_dir / filename

    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return output_path


def split_podcast_episode(episode_path: Path, output_dir: Path) -> List[Path]:
    """Split the podcast episode into 10-minute segments using ffmpeg.
    Returns list of segment file paths."""
    segment_duration = 60 * 10  # 10 minutes in seconds
    segment_pattern = output_dir / "segment_%03d.mp3"

    # Use ffmpeg to split the file
    ffmpeg_cmd = os.getenv('FFMPEG_PATH', 'ffmpeg')
    cmd = [
        ffmpeg_cmd,
        '-i', str(episode_path),
        '-f', 'segment',
        '-segment_time', str(segment_duration),
        '-c', 'copy',
        str(segment_pattern)
    ]

    subprocess.run(cmd, check=True, capture_output=True)

    # Find all generated segments
    segments = sorted(output_dir.glob("segment_*.mp3"))
    return segments


def generate_audio_intro(episode_number: int, index: int, total: int, output_dir: Path) -> Path:
    """Generate an intro audio segment for the given index out of total segments. e.g. "1 of 5"
    Returns path to the generated audio file.
    Uses piper to generate the audio in the format: "{index}_of_{total}.mp3"
    """
    text = f"{index} of {total}.{episode_number}"
    wav_output = output_dir / f"intro_{index}_of_{total}.wav"
    mp3_output = output_dir / f"intro_{index}_of_{total}.mp3"

    # Use piper to generate the speech (outputs WAV)
    # Note: You may need to specify a voice model path with --model
    piper_cmd_parts = os.getenv('PIPER_CMD', 'piper').split()
    piper_model = os.getenv('PIPER_VOICE_MODEL_PATH',
                            '/voices/en_US-hfc_female-medium.onnx')
    cmd = [
        *piper_cmd_parts,
        '-m', piper_model,
        '-f', str(wav_output),
        '--', text
    ]

    # Pipe the text to piper via stdin
    subprocess.run(cmd, check=True, capture_output=True)

    # Convert WAV to MP3 using ffmpeg
    ffmpeg_cmd = os.getenv('FFMPEG_PATH', 'ffmpeg')
    cmd = [
        ffmpeg_cmd,
        '-i', str(wav_output),
        '-codec:a', 'libmp3lame',
        '-b:a', '128k',
        str(mp3_output)
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    return mp3_output


def merge_intro_and_segment(segment_path: Path, intro_path: Path, output_dir: Path, index: int) -> Path:
    """Merge intro audio and segment into a single audio file with 1 second silence between them.
    Returns path to the merged file."""
    output_path = output_dir / f"final_segment_{index:03d}.mp3"

    # Generate 0.5 second of silence
    silence_path = output_dir / f"silence_{index}.mp3"
    ffmpeg_cmd = os.getenv('FFMPEG_PATH', 'ffmpeg')
    silence_cmd = [
        ffmpeg_cmd,
        '-f', 'lavfi',
        '-i', 'anullsrc=r=44100:cl=stereo',
        '-t', '0.5',
        '-codec:a', 'libmp3lame',
        '-b:a', '128k',
        str(silence_path)
    ]
    subprocess.run(silence_cmd, check=True, capture_output=True)

    # Create a temporary file list for ffmpeg concat
    concat_list_path = output_dir / f"concat_list_{index}.txt"
    with open(concat_list_path, 'w') as f:
        f.write(f"file '{intro_path.absolute()}'\n")
        f.write(f"file '{silence_path.absolute()}'\n")
        f.write(f"file '{segment_path.absolute()}'\n")

    # Use ffmpeg to concatenate the files
    # Re-encode to ensure consistent format/bitrate instead of using -c copy
    cmd = [
        ffmpeg_cmd,
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_list_path),
        '-codec:a', 'libmp3lame',
        '-b:a', '128k',
        str(output_path)
    ]

    subprocess.run(cmd, check=True, capture_output=True)

    return output_path
