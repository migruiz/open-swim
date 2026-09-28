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

**Sync triggers:** MQTT (re)connect, device plugged in, every `SYNC_INTERVAL_HOURS`, and `SELECTION_SYNC_DELAY_SECONDS` after the last change to a selection topic (debounced so ticking episodes one by one starts one sync). Unplugged, a sync only downloads to the library; plugged in, it also copies to the device.

**Threading model:** Single queue + daemon worker thread in `sync.py`. `enqueue_sync()` adds tasks, `_sync_worker()` processes serially to prevent overlapping downloads/device writes. At most one sync waits behind the running one; further triggers are dropped because the waiting one covers them.

**Device mounting (Linux):** the monitor only records that the player is present. `sync.work()` mounts it (`ensure_mounted`) right before copying and flushes + unmounts it (`release_device`) right after, then publishes `safe_to_unplug`, so pulling the player out between syncs cannot corrupt its FAT filesystem.

**yt-dlp freshness:** in Docker the standalone binary lives on the `ytdlp-bin` volume. `docker-entrypoint.sh` updates it on every start and daily at `YTDLP_UPDATE_TIME`; `media/youtube/ytdlp.py` also updates and retries once when a yt-dlp call fails (at most hourly).

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
- Device `sync_state.json` at the SD root - per-playlist SHA256 of the video IDs that were actually copied (only those ready in the library), plus the copied podcast episode IDs; a video or episode that finishes downloading later changes these and gets copied next sync

**MQTT contract:**
- Subscribe:
  - `openswim/episodes_to_sync` - JSON array of podcast episodes to sync
  - `openswim/playlists_to_sync` - JSON array of `{id, title}` for YouTube playlists
  - `openswim/playlist-info/request` - Request playlist metadata
- Publish:
  - `openswim/device/status` (retained) - `{status: "connected"|"safe_to_unplug"|"disconnected", device, mount_point, timestamp}`
  - `openswim/sync/progress` - Real-time sync progress with phase, status, and percentage
  - `openswim/playlist-info/response` - Playlist metadata response

## External Dependencies

Requires on PATH (or via env vars): `yt-dlp`, `ffmpeg`, `piper` with voice model

## Environment Variables

- `MQTT_BROKER_URI` (required) - `mqtt://host:port`
- `LIBRARY_PATH` (default `/library`) - Root for youtube/ and podcasts/
- `YTDLP_PATH`, `FFMPEG_PATH` - Custom binary paths
- `PIPER_CMD`, `PIPER_VOICE_MODEL_PATH` - Piper TTS for podcast intros
- `OPEN_SWIM_SD_PATH` - Device mount point (Linux: where the device is mounted during a copy, e.g. `/mnt/openswim`; Windows: the player's drive, e.g. `E:\` - not auto-detected)
- `PLAYLIST_SYNC_LIMIT` (default 20) - Newest N videos per playlist that are downloaded and copied
- `SYNC_INTERVAL_HOURS` (default 2, 0 disables) - Automatic sync interval
- `SELECTION_SYNC_DELAY_SECONDS` (default 120) - Quiet period after a selection change before syncing
- `LIBRARY_PRUNE` (default false; true on the Pi) - Delete library files no longer selected. Skipped when a selection is empty or the playlist fetch failed
- `YTDLP_UPDATE_CHANNEL` (Docker: nightly) - Channel for yt-dlp self-updates; empty means plain `-U`
- `YTDLP_UPDATE_TIME` (Docker: 00:00) - Daily yt-dlp update time, container local time
- `YTDLP_PLAYER_CLIENT` - yt-dlp player client override. Leave unset in Docker (deno is installed and the default client works); `mweb` fails there for lack of a PO token

## Raspberry Pi deployment

`docker-compose.yml` is the Portainer stack on the Pi. Build and push the arm64 image with `build-push-arm64.bat`, then pull and redeploy the stack in Portainer.

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
- YouTube playlist sync is limited to the newest `PLAYLIST_SYNC_LIMIT` (20) items, for both the library download and the device copy (`videos_to_sync()` in `media/youtube/playlists.py`).
- `uv run --extra dev pytest` runs the tests; `test_sanitize.py::test_special_characters_removed` is a known failure that predates the Pi sync work.
