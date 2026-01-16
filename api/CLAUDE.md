# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                    # Install dependencies
uv run open-swim           # Launch MQTT listener + device monitor + sync worker
uv run mypy src/           # Type check (strict mode enabled)
```

One-off sync without MQTT/device monitor:
```bash
uv run python -c "from open_swim.sync import work; work()"
```

## Architecture

Long-running MQTT worker that normalizes YouTube playlists and podcast episodes into a local library, then mirrors playlists onto an OpenSwim MP3 player via folder-per-playlist copy with hash-based change detection.

**Runtime flow:** `app.py` starts a background device monitor and MQTT client, blocks in MQTT loop. On connect, subscribes to topics and enqueues initial sync.

**Threading model:** Single queue + daemon worker thread in `sync.py`. `enqueue_sync()` adds tasks, `_sync_worker()` processes serially to prevent overlapping downloads/device writes.

**Primary code paths:**
- `src/open_swim/app.py` - Entry point, MQTT/device wiring
- `src/open_swim/sync.py` - Queue orchestrator (thread-safe worker)
- `src/open_swim/media/youtube/` - Download, normalize, playlist handling, TTS intro generation
- `src/open_swim/media/podcast/` - Download, split into 10-min segments, Piper TTS intros
- `src/open_swim/device/` - Platform-specific device monitoring and sync
  - `linux/` - Uses `blkid`/`mount`/`umount` for device detection
  - `windows/` - Uses Win32 API via ctypes (`GetLogicalDrives`, `GetVolumeInformationW`)
  - `sync/` - Copy logic for YouTube playlists and podcasts to device

**State management (file-based):**
- `LIBRARY_PATH/youtube/info.json` - Downloaded/normalized YouTube videos (keyed by video ID)
- `LIBRARY_PATH/youtube/playlists_to_sync.json` - Requested playlist IDs + titles
- `LIBRARY_PATH/podcasts/info.json` - Processed podcast episodes
- `LIBRARY_PATH/podcasts/episodes_to_sync.json` - Requested episodes
- Device `sync.json` per playlist folder - SHA256 hash of video IDs for change detection

**MQTT contract:**
- Subscribe:
  - `openswim/episodes_to_sync` - JSON array of podcast episodes to sync
  - `openswim/playlists_to_sync` - JSON array of `{id, title}` for YouTube playlists
  - `openswim/playlist-info/request` - Request playlist metadata
- Publish:
  - `openswim/device/status` (retained) - `{status: "connected"|"disconnected", device, mount_point, timestamp}`
  - `openswim/sync/progress` - Real-time sync progress with phase, status, and percentage
  - `openswim/playlist-info/response` - Playlist metadata response

## External Dependencies

Requires on PATH (or via env vars): `yt-dlp`, `ffmpeg`, `piper` with voice model

## Environment Variables

- `MQTT_BROKER_URI` (required) - `mqtt://host:port`
- `LIBRARY_PATH` (default `/library`) - Root for youtube/ and podcasts/
- `YTDLP_PATH`, `FFMPEG_PATH` - Custom binary paths
- `PIPER_CMD`, `PIPER_VOICE_MODEL_PATH` - Piper TTS for podcast intros
- `OPEN_SWIM_SD_PATH` - Device mount point (Linux: where device is mounted, e.g., `/mnt/openswim`; Windows: auto-detected from drive letter)

## Running on Windows

```bash
uv sync                    # Install dependencies
uv run open-swim           # Launch with Windows device monitor
```

Ensure `yt-dlp`, `ffmpeg`, and optionally `piper` are installed and on PATH. The Windows device monitor uses Win32 API to detect removable drives labeled "OpenSwim" - no manual mounting required.

## Development Notes

- DeviceMonitor is platform-aware: `create_device_monitor()` in `device/__init__.py` returns `WindowsDeviceMonitor` on Windows or `LinuxDeviceMonitor` on Linux/RPi/container. Both auto-detect USB drives labeled "OpenSwim".
- On Windows, drives auto-mount to letters (e.g., `E:\`); on Linux, explicit mount to `OPEN_SWIM_SD_PATH` is performed.
- Download-heavy steps (yt-dlp, ffmpeg, Piper) trigger significant network/CPU; avoid during code review.
- Syncing to device wipes and recreates playlist folders before copying; use test media when experimenting.
- Delete `info.json` files to clear cached library state.
- Simulate MQTT by publishing to topics with JSON payloads.
- YouTube playlist sync is limited to the last 20 items.
