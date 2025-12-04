import re
import subprocess
from pathlib import Path
from typing import List

from open_swim.config import config
from open_swim.media.podcast.episodes_to_sync import EpisodeToSync
  





def get_episode_segments(episode: EpisodeToSync, episode_path: Path, tmp_path: Path) -> List[Path]:
    """Split a podcast episode, generate intros, and merge segments."""
    print("Splitting podcast into 10-minute segments...")
    segment_paths = _split_podcast_episode(episode_path=episode_path, output_dir=tmp_path)

    total_segments = len(segment_paths)
    print(f"Processing {total_segments} segments...")
    final_segments: List[Path] = []
    for index, segment_path in enumerate(segment_paths, start=1):
        print(f"Processing segment {index} of {total_segments}...")

        intro_path = _generate_audio_intro(episode=episode, index=index, total=total_segments, output_dir=tmp_path)
        merged_path = _merge_intro_and_segment(
            episode=episode,
            segment_path=segment_path,
            intro_path=intro_path,
            output_dir=tmp_path,
            index=index,
        )
        final_segments.append(merged_path)

    return final_segments


def _split_podcast_episode(episode_path: Path, output_dir: Path) -> List[Path]:
    """Split the podcast episode into 10-minute segments using ffmpeg.
    Returns list of segment file paths."""
    segment_duration = 60 * 10  # 10 minutes in seconds
    segment_pattern = output_dir / "segment_%03d.mp3"

    # Use ffmpeg to split the file
    cmd = [
        config.ffmpeg_path,
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


def _generate_audio_intro(episode: EpisodeToSync, index: int, total: int, output_dir: Path) -> Path:
    """Generate an intro audio segment for the given index out of total segments. e.g. "1 of 5"
    Returns path to the generated audio file.
    Uses piper to generate the audio in the format: "{index}_of_{total}.mp3"
    """
    #convert episode.date to "November 5th"
    date_str = episode.date.strftime("%B %d")
    text  = f"{date_str}. {index} of {total}"
    wav_output = output_dir / f"intro_{index}_of_{total}.wav"
    mp3_output = output_dir / f"intro_{index}_of_{total}.mp3"

    # Use piper to generate the speech (outputs WAV)
    piper_cmd_parts = config.piper_cmd.split()
    cmd = [
        *piper_cmd_parts,
        '-m', config.piper_voice_model_path,
        '-f', str(wav_output),
        '--', text
    ]

    # Pipe the text to piper via stdin
    subprocess.run(cmd, check=True, capture_output=True)

    # Convert WAV to MP3 using ffmpeg
    cmd = [
        config.ffmpeg_path,
        '-i', str(wav_output),
        '-codec:a', 'libmp3lame',
        '-b:a', '128k',
        str(mp3_output)
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    return mp3_output


def _merge_intro_and_segment(episode: EpisodeToSync, segment_path: Path, intro_path: Path, output_dir: Path, index: int) -> Path:
    """Merge intro audio and segment into a single audio file with 1 second silence between them.
    Returns path to the merged file."""
    sanitized_title = re.sub(r'[^\w\s-]', '', episode.title)
    sanitized_title = re.sub(r'[\s]+', '_', sanitized_title.strip())
    output_path = output_dir / f"{sanitized_title}_{episode.id}_{index:03d}.mp3"

    # Generate 0.5 second of silence
    silence_path = output_dir / f"silence_{episode.id}_{index}.mp3"
    silence_cmd = [
        config.ffmpeg_path,
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
        config.ffmpeg_path,
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_list_path),
        '-codec:a', 'libmp3lame',
        '-b:a', '128k',
        str(output_path)
    ]

    subprocess.run(cmd, check=True, capture_output=True)

    return output_path
