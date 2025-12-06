# Open Swim

Open Swim is a small Python worker that listens to MQTT commands, builds a normalized offline library from YouTube playlists and podcast feeds, and syncs that library to an OpenSwim MP3 player.

## How it works
- Starts an MQTT client and a device monitor. On connect it subscribes to playlist and podcast instructions and immediately enqueues a sync.
- Messages on `openswim/episodes_to_sync` and `openswim/playlists_to_sync` are persisted to disk; the sync worker reads those requests and processes them sequentially to avoid overlapping downloads.
- YouTube videos are downloaded with `yt-dlp`, normalized with `ffmpeg`, and stored under `LIBRARY_PATH/youtube` with metadata in `info.json`.
- Podcast episodes are downloaded via HTTP, split into 10-minute chunks, prefixed with Piper-generated intros, and stored under `LIBRARY_PATH/podcasts` with metadata in `info.json`.
- A device sync step copies normalized audio onto the mounted OpenSwim storage, one folder per playlist, and skips work when a playlist hash has not changed.

## Requirements
- Python 3.11+ and `uv`
- External binaries on PATH (or set env vars below): `ffmpeg`, `yt-dlp`, and `piper` with a voice model (see Dockerfile stage for example downloads)
- MQTT broker reachable from the runtime
- If syncing a device: Linux host permissions to mount block devices (container uses `--privileged`)

## Configuration
Set via environment variables or a local `.env` loaded on start:
- `MQTT_BROKER_URI` (required): `mqtt://host:port`
- `LIBRARY_PATH` (default `/library`): root directory for `youtube/` and `podcasts/`
- `YTDLP_PATH`, `FFMPEG_PATH`: custom paths to those binaries
- `PIPER_CMD`, `PIPER_VOICE_MODEL_PATH`: Piper executable and voice model for podcast intros
- `OPEN_SWIM_SD_PATH`: mount path of the device storage when syncing playlists to hardware

## Run locally
```powershell
uv sync
uv run open-swim            # launches MQTT listener + device monitor + sync worker
```

Trigger a one-off sync without MQTT:
```powershell
uv run python - <<'PY'
from open_swim.sync import work
work()
PY
```

## MQTT contract
- Subscribes: `openswim/episodes_to_sync` (JSON array of `{id, date, download_url, title}`); `openswim/playlists_to_sync` (JSON array of `{id, title}` where id is the playlist id).
- Publishes: `openswim/device/status` with `status` (`connected`/`disconnected`), `device`, `mount_point`, and a timestamp; retained to advertise current state.

## Library and device layout
- `LIBRARY_PATH/podcasts/episodes_to_sync.json`: persisted incoming podcast requests
- `LIBRARY_PATH/podcasts/info.json`: known processed episodes and their output folders
- `LIBRARY_PATH/youtube/playlists_to_sync.json`: playlist ids requested for sync
- `LIBRARY_PATH/youtube/info.json`: normalized YouTube tracks and their paths
- Device sync writes one folder per playlist to `OPEN_SWIM_SD_PATH` and stores `sync.json` inside each to record the last synced hash.

## Containers
- Build (arm64 example): `docker buildx build --platform linux/arm64 -t open-swim:0.1.0 .`
- Runtime needs `--privileged` (for mounting), `/dev` passed through, and the target mount (default `/mnt/openswim`) bind-mounted. See `docker-compose.yml` for the baseline service.

## Development notes
- Entry point: `src/open_swim/app.py`; CLI shim: `src/open_swim/main.py`.
- Background sync queue is started at import time in `open_swim.sync`; long-running calls (ffmpeg, yt-dlp, Piper) occur inside worker tasks.
- Device detection is Linux-specific (`blkid`/`mount`/`umount`). On Windows the monitor is skipped; on Linux/RPi/container it auto-starts. Set `OPEN_SWIM_SD_PATH` when running without the monitor.
