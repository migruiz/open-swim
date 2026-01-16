# Implementation Plan: mqtt-client-api

## Overview
Add MQTT-based YouTube playlist info lookup and sync progress publishing to enable the Flutter client to fetch playlist metadata and monitor sync operations in real-time.

## Files to Modify/Create

| File | Action | Purpose |
|------|--------|---------|
| `src/open_swim/messaging/models.py` | Create | Pydantic models for request/response/progress messages |
| `src/open_swim/messaging/progress.py` | Create | ProgressReporter protocol and MqttProgressReporter implementation |
| `src/open_swim/messaging/__init__.py` | Modify | Export new modules |
| `src/open_swim/app.py` | Modify | Add accessor, playlist handler, subscribe to new topic |
| `src/open_swim/media/youtube/library_sync.py` | Modify | Replace prints with progress reporting |
| `src/open_swim/media/podcast/sync.py` | Modify | Replace prints with progress reporting |
| `src/open_swim/media/podcast/episode_processor.py` | Modify | Add progress reporting for segments |
| `src/open_swim/device/sync/youtube/device_youtube_sync.py` | Modify | Replace prints with progress reporting |
| `src/open_swim/device/sync/podcast/device_podcast_sync.py` | Modify | Replace prints with progress reporting |

## Implementation Steps

### Step 1: Create Messaging Models
**Files:** `src/open_swim/messaging/models.py`
- [ ] Create `PlaylistInfoRequest` model with `playlist_id: str` field
- [ ] Create `PlaylistInfoVideoItem` model with `id`, `title` fields
- [ ] Create `PlaylistInfoResponse` model with `success`, `playlist_id`, `title`, `videos`, `error` fields
- [ ] Create `SyncPhase` enum: `youtube_library`, `podcast_library`, `device_youtube`, `device_podcast`
- [ ] Create `SyncItemStatus` enum: `started`, `downloading`, `normalizing`, `segmenting`, `copying`, `completed`, `skipped`, `error`
- [ ] Create `SyncProgressMessage` model with phase, status, item details, progress fields, timestamp

### Step 2: Create Progress Reporter
**Files:** `src/open_swim/messaging/progress.py`
- [ ] Define `ProgressReporter` Protocol with `report_progress()` method
- [ ] Implement `MqttProgressReporter` class that:
  - Takes MqttClient in constructor
  - Publishes to `openswim/sync/progress` topic
  - Calculates percentage from current_index/total_count
  - Prints to console (preserves existing behavior)
  - Handles publish failures gracefully (don't fail sync)
- [ ] Implement `NullProgressReporter` for testing/fallback

### Step 3: Update Messaging __init__.py
**Files:** `src/open_swim/messaging/__init__.py`
- [ ] Export models and progress reporter classes

### Step 4: Update App Entry Point
**Files:** `src/open_swim/app.py`
- [ ] Add import for progress reporter
- [ ] Add `_progress_reporter` module-level variable
- [ ] Add `get_progress_reporter()` accessor function
- [ ] Initialize `MqttProgressReporter` in `run()` after creating MqttClient
- [ ] Subscribe to `openswim/playlist-info/request` in `_on_mqtt_connected()`
- [ ] Add `_handle_playlist_info_request()` function that:
  - Parses request JSON
  - Normalizes playlist_id (handles both URL and ID)
  - Calls `fetch_playlist_information()` in background thread
  - Publishes response to `openswim/playlist-info/response`
- [ ] Add case for `openswim/playlist-info/request` in `_on_mqtt_message()` match

### Step 5: Update YouTube Library Sync
**Files:** `src/open_swim/media/youtube/library_sync.py`
- [ ] Import `get_progress_reporter` and models
- [ ] Update `_sync_library_playlist()`:
  - Get reporter at start
  - Track total video count
  - Report progress for each video with current_index/total_count
- [ ] Update `_sync_video_to_library()`:
  - Add reporter, index, total parameters
  - Report DOWNLOADING status before download
  - Report NORMALIZING status before normalize
  - Report COMPLETED status after success
- [ ] Update error handling to report ERROR status with error_message

### Step 6: Update Podcast Library Sync
**Files:** `src/open_swim/media/podcast/sync.py`
- [ ] Import `get_progress_reporter` and models
- [ ] Report progress for each episode download/process
- [ ] Report SEGMENTING status during segment generation
- [ ] Report errors with episode details

### Step 7: Update Podcast Episode Processor
**Files:** `src/open_swim/media/podcast/episode_processor.py`
- [ ] Accept reporter parameter
- [ ] Report segment progress (current segment / total segments)

### Step 8: Update Device YouTube Sync
**Files:** `src/open_swim/device/sync/youtube/device_youtube_sync.py`
- [ ] Import `get_progress_reporter` and models
- [ ] Report DEVICE_YOUTUBE phase progress
- [ ] Report per-playlist start/complete
- [ ] Report per-file COPYING status
- [ ] Report SKIPPED for already up-to-date playlists
- [ ] Report ERROR for missing videos/files

### Step 9: Update Device Podcast Sync
**Files:** `src/open_swim/device/sync/podcast/device_podcast_sync.py`
- [ ] Import `get_progress_reporter` and models
- [ ] Report DEVICE_PODCAST phase progress
- [ ] Report per-file COPYING status
- [ ] Report SKIPPED for already up-to-date episodes

### Step 10: Verification
- [ ] Run `uv run mypy src/` - type checking passes
- [ ] Test playlist info request via MQTT client (e.g., MQTT Explorer)
- [ ] Verify progress messages published during sync
- [ ] Verify console output still works
- [ ] Verify errors are captured in progress messages

## Message Schema Reference

### Playlist Info Request
```json
{"playlist_id": "PLxxx"}
// or
{"playlist_id": "https://youtube.com/playlist?list=PLxxx"}
```

### Playlist Info Response
```json
{
  "success": true,
  "playlist_id": "PLxxx",
  "title": "My Playlist",
  "videos": [{"id": "abc", "title": "Video 1"}]
}
```

### Sync Progress Message
```json
{
  "phase": "youtube_library",
  "playlist_id": "PLxxx",
  "playlist_title": "My Playlist",
  "item_id": "abc",
  "item_title": "Video 1",
  "status": "downloading",
  "current_index": 1,
  "total_count": 10,
  "percentage": 10.0,
  "timestamp": "2025-12-12T10:30:00Z"
}
```

## Notes for Implementers
- paho-mqtt `publish()` is thread-safe - safe to call from sync worker thread
- Use QoS 0 for progress messages (high frequency, loss acceptable)
- Use QoS 1 for playlist info response (should be delivered)
- Keep existing print() statements alongside MQTT publishing
- `fetch_playlist_information()` has 60s timeout - run in background thread for playlist info requests
- Import `get_progress_reporter` from `open_swim.app` to avoid circular imports