# Implementation Plan: youtube-audio-intro

## Overview
Add audio intro generation to YouTube library sync by creating a new `intro_processor.py` module that generates TTS intros using Piper, then merges them with the normalized MP3. The sync flow will be updated to call this after normalization, before saving to the library.

## Files to Modify/Create
| File | Action | Purpose |
|------|--------|---------|
| src/open_swim/media/youtube/intro_processor.py | Create | TTS intro generation and merging logic |
| src/open_swim/media/youtube/models.py | Modify | Add ADDING_INTRO to VideoStatus enum |
| src/open_swim/media/youtube/library_sync.py | Modify | Integrate intro processing into sync flow |

## Implementation Steps

### Step 1: Add ADDING_INTRO status to VideoStatus enum
**Files:** `src/open_swim/media/youtube/models.py`
- [ ] Add `ADDING_INTRO = "adding_intro"` to VideoStatus enum (between NORMALIZING and READY)

### Step 2: Create intro_processor.py module
**Files:** `src/open_swim/media/youtube/intro_processor.py`
- [ ] Create new file with imports: subprocess, Path, secrets, re, config, YoutubeVideo
- [ ] Implement `_generate_title_audio(video: YoutubeVideo, output_dir: Path) -> Path`:
  - Generate WAV using Piper with video.title as text
  - Convert WAV to MP3 using ffmpeg (128k bitrate)
  - Return path to MP3 intro file
- [ ] Implement `_generate_silence(output_dir: Path, video_id: str) -> Path`:
  - Generate 0.5 second silence MP3 using ffmpeg lavfi anullsrc
  - Return path to silence file
- [ ] Implement `add_intro_to_video(video: YoutubeVideo, normalized_mp3_path: Path, output_dir: Path) -> Path`:
  - Call `_generate_title_audio()` to create intro
  - Call `_generate_silence()` to create silence
  - Create concat list file with: intro + silence + normalized_mp3
  - Use ffmpeg concat demuxer to merge (re-encode at 128k)
  - Return path to final MP3 with intro

Reference implementation from podcast episode_processor.py lines 57-134.

### Step 3: Integrate into library_sync.py
**Files:** `src/open_swim/media/youtube/library_sync.py`
- [ ] Add import: `from open_swim.media.youtube.intro_processor import add_intro_to_video`
- [ ] In `_sync_video_to_library()`, after normalization (line 52):
  - Add `update_video_status(video.id, VideoStatus.ADDING_INTRO)`
  - Call `final_mp3_path = add_intro_to_video(video, temp_normalized_mp3_path, tmp_path)`
  - Pass `final_mp3_path` instead of `temp_normalized_mp3_path` to `add_normalized_mp3_to_library()`

Updated flow:
```python
# After line 52 (normalization)
update_video_status(video.id, VideoStatus.ADDING_INTRO)
final_mp3_path = add_intro_to_video(
    video=video,
    normalized_mp3_path=temp_normalized_mp3_path,
    output_dir=tmp_path,
)
add_normalized_mp3_to_library(
    youtube_video=video,
    temp_normalized_mp3_path=final_mp3_path,  # Changed from temp_normalized_mp3_path
    playlist_id=playlist_id,
)
```

### Step 4: Verification
- [ ] Run `uv run mypy src/` - type checking passes
- [ ] Manually test by syncing a YouTube playlist and verifying:
  - Status transitions through ADDING_INTRO
  - Final MP3 starts with spoken title
  - 0.5 second silence between intro and content
  - Audio quality maintained (128k bitrate)

## Notes for Implementers
- The intro_processor should mirror the podcast episode_processor.py patterns closely
- Use `secrets.token_hex(8)` for unique temp filenames (consistent with existing code)
- Config values for Piper come from `config.piper_cmd` and `config.piper_voice_model_path`
- ffmpeg path comes from `config.ffmpeg_path`
- All temp files are in the temp directory which gets auto-cleaned