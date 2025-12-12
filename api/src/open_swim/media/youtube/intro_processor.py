import re
import secrets
import subprocess
from pathlib import Path

from open_swim.config import config
from open_swim.media.youtube.playlists import YoutubeVideo


def _generate_title_audio(video: YoutubeVideo, output_dir: Path) -> Path:
    """Generate an MP3 TTS intro speaking the video title."""
    safe_title = re.sub(r"\s+", " ", video.title or "").strip()
    if not safe_title:
        safe_title = "Unknown title"

    token = secrets.token_hex(16)
    wav_output = output_dir / f"intro_{video.id}_{token}.wav"
    mp3_output = output_dir / f"intro_{video.id}_{token}.mp3"

    piper_cmd_parts = config.piper_cmd.split()
    cmd = [
        *piper_cmd_parts,
        "-m",
        config.piper_voice_model_path,
        "-f",
        str(wav_output),
        "--",
        safe_title,
    ]
    subprocess.run(cmd, check=True, capture_output=True)

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
    return mp3_output


def _generate_silence(output_dir: Path, video_id: str) -> Path:
    """Generate 0.5 seconds of silence as an MP3."""
    token = secrets.token_hex(16)
    silence_path = output_dir / f"silence_{video_id}_{token}.mp3"
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
    return silence_path


def add_intro_to_video(video: YoutubeVideo, normalized_mp3_path: str, output_dir: Path) -> str:
    """Add a spoken title intro to a normalized YouTube MP3 and return new path."""
    intro_path = _generate_title_audio(video=video, output_dir=output_dir)
    silence_path = _generate_silence(output_dir=output_dir, video_id=video.id)

    output_path = output_dir / f"intro_added_{video.id}_{secrets.token_hex(16)}.mp3"

    concat_list_path = output_dir / f"concat_list_{video.id}_{secrets.token_hex(16)}.txt"
    with open(concat_list_path, "w", encoding="utf-8") as f:
        f.write(f"file '{intro_path.absolute()}'\n")
        f.write(f"file '{silence_path.absolute()}'\n")
        f.write(f"file '{Path(normalized_mp3_path).absolute()}'\n")

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

