import os
import secrets
import subprocess
from pathlib import Path

from open_swim.config import config
from open_swim.media.youtube.playlists import YoutubeVideo


def _generate_title_audio(video: YoutubeVideo, output_dir: Path) -> str:
    """Generate TTS audio of the video title using Piper.

    Returns path to the generated MP3 file.
    """
    unique_id = secrets.token_hex(8)
    wav_output = output_dir / f"intro_{video.id}_{unique_id}.wav"
    mp3_output = output_dir / f"intro_{video.id}_{unique_id}.mp3"

    # Use piper to generate the speech (outputs WAV)
    piper_cmd_parts = config.piper_cmd.split()
    cmd = [
        *piper_cmd_parts,
        "-m",
        config.piper_voice_model_path,
        "-f",
        str(wav_output),
        "--",
        video.title,
    ]

    subprocess.run(cmd, check=True, capture_output=True)

    # Convert WAV to MP3 using ffmpeg
    cmd = [
        config.ffmpeg_path,
        "-i",
        str(wav_output),
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(mp3_output),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    return str(mp3_output)


def _generate_silence(output_dir: Path, video_id: str) -> str:
    """Generate 0.5 second silence MP3 using ffmpeg.

    Returns path to the silence file.
    """
    unique_id = secrets.token_hex(8)
    silence_path = output_dir / f"silence_{video_id}_{unique_id}.mp3"

    cmd = [
        config.ffmpeg_path,
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=stereo",
        "-t",
        "0.5",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(silence_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    return str(silence_path)


def add_intro_to_video(
    video: YoutubeVideo, normalized_mp3_path: str, output_dir: Path
) -> str:
    """Add a spoken title intro to the video audio.

    Generates TTS intro, adds 0.5 second silence, then merges with video audio.
    Returns path to the final MP3 with intro.
    """
    intro_path = _generate_title_audio(video=video, output_dir=output_dir)
    silence_path = _generate_silence(output_dir=output_dir, video_id=video.id)

    unique_id = secrets.token_hex(8)
    concat_list_path = output_dir / f"concat_list_{video.id}_{unique_id}.txt"
    output_path = output_dir / f"with_intro_{video.id}_{unique_id}.mp3"

    # Create concat list file
    with open(concat_list_path, "w") as f:
        f.write(f"file '{os.path.abspath(intro_path)}'\n")
        f.write(f"file '{os.path.abspath(silence_path)}'\n")
        f.write(f"file '{os.path.abspath(normalized_mp3_path)}'\n")

    # Use ffmpeg to concatenate the files with re-encoding
    cmd = [
        config.ffmpeg_path,
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list_path),
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    return str(output_path)
