# Implementation Plan: fix-sync-state-on-error

## Overview
Modify the exception handling in both device sync files to catch copy errors, add meaningful context, and re-raise. This ensures the sync state is never saved when errors occur, allowing automatic recovery on the next sync.

## Files to Modify/Create
| File | Action | Purpose |
|------|--------|---------|
| `src/open_swim/device/sync/youtube/device_youtube_sync.py` | Modify | Change exception handling to re-raise with context |
| `src/open_swim/device/sync/podcast/device_podcast_sync.py` | Modify | Change exception handling to re-raise with context |

## Implementation Steps

### Step 1: Fix YouTube device sync
**Files:** `src/open_swim/device/sync/youtube/device_youtube_sync.py`

Change lines 66-70 from:
```python
        try:
            shutil.copy2(video_info.mp3_path, destination_path)
            print(f"[Device Sync] Copied: {filename} -> {playlist_title}/")
        except Exception as e:
            print(f"[Device Sync] Error copying {filename}: {e}")
```

To:
```python
        try:
            shutil.copy2(video_info.mp3_path, destination_path)
            print(f"[Device Sync] Copied: {filename} -> {playlist_title}/")
        except Exception as e:
            raise RuntimeError(
                f"[Device Sync] Failed to copy '{filename}' to playlist '{playlist_title}': {e}"
            ) from e
```

### Step 2: Fix podcast device sync
**Files:** `src/open_swim/device/sync/podcast/device_podcast_sync.py`

Change lines 81-85 from:
```python
            try:
                shutil.copy2(mp3_file, destination_path)
                print(f"[Podcast Sync] Copied: {filename}")
            except Exception as e:
                print(f"[Podcast Sync] Error copying {filename}: {e}")
```

To:
```python
            try:
                shutil.copy2(mp3_file, destination_path)
                print(f"[Podcast Sync] Copied: {filename}")
            except Exception as e:
                raise RuntimeError(
                    f"[Podcast Sync] Failed to copy '{filename}' for episode '{episode.id}': {e}"
                ) from e
```

### Step 3: Verification
- [ ] Run `uv run mypy src/` to verify type checking passes
- [ ] Manually test by simulating a copy failure (e.g., read-only destination, disk full)
- [ ] Verify that after a failure, the next sync re-processes the affected playlist/podcast

## Notes for Implementers
- The `from e` syntax preserves the original exception chain for debugging
- `RuntimeError` is appropriate here as it represents a runtime failure during sync
- The sync state update code (lines 74-79 in youtube, lines 87-88 in podcast) will never execute when an exception is raised, which is the desired behavior
- The upper-level handler in `sync.py:23` will catch and log the full traceback