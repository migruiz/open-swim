# Architecture

Open Swim is a long-running worker that reacts to MQTT messages, shapes media into a normalized offline library, and syncs that library to an OpenSwim MP3 player. The code favors simple, sequential operations and file-based state so it can run reliably on low-resource devices or inside a container.

## Top-level runtime
- `open_swim.app.run()` sets up a background device monitor and an MQTT client, then blocks in the MQTT loop. On connect it subscribes to playlist and podcast topics and enqueues an initial sync.
- `open_swim.sync` owns a single queue and worker thread (`enqueue_sync` -> `_sync_worker` -> `work`) to guarantee only one sync runs at a time.
- Environment variables are loaded via `python-dotenv` at process start; most components read their own paths or binary overrides.

## MQTT contract
- Subscribed topics
  - `openswim/episodes_to_sync`: JSON array of podcast episodes (`id`, ISO `date`, `download_url`, `title`). Persisted to `LIBRARY_PATH/podcasts/episodes_to_sync.json`.
  - `openswim/playlists_to_sync`: JSON array of playlist ids and titles (`id`, `title`). Persisted to `LIBRARY_PATH/youtube/playlists_to_sync.json`.
- Published topic
  - `openswim/device/status` (retained): `{status, device, mount_point, timestamp}` whenever the device mounts/unmounts and on startup once the MQTT client is ready.

## Podcast pipeline
1. `load_episodes_to_sync()` reads the pending episode list from disk.
2. `_process_podcast_episode()` skips work if the episode already exists in `info.json`.
3. Downloads the episode via `requests` to a temp directory.
4. Splits the MP3 into 10-minute segments using `ffmpeg` (`segment` muxer).
5. For each segment, generates a spoken intro with Piper (`PIPER_CMD`/`PIPER_VOICE_MODEL_PATH`), inserts 0.5s of silence, and concatenates intro + silence + segment into a re-encoded MP3.
6. Copies the final segments into `LIBRARY_PATH/podcasts/<sanitized_title>_<id>/` and records the episode in `info.json`.

## YouTube pipeline
1. `get_playlists_to_sync()` loads playlist ids from disk and builds playlist URLs.
2. `fetch_playlist()` uses `yt-dlp --dump-single-json --flat-playlist` to enumerate videos (id, title, uploader info).
3. `_sync_video_to_library()` downloads each track with `yt-dlp`, normalizes loudness via `ffmpeg loudnorm` to 128 kbps, and stores it under `LIBRARY_PATH/youtube/` with a filename like `<title>__normalized__<videoId>.mp3`.
4. Library metadata is kept in `LIBRARY_PATH/youtube/info.json` keyed by video id for quick “already downloaded” checks.

## Device detection and sync
- `DeviceMonitor` (Linux-only) scans `/dev/*` for block devices labeled `OpenSwim`, mounts them at `/mnt/openswim` (or OS default), and emits connect/disconnect callbacks. Mount/unmount uses `mount`/`umount`. On Windows dev hosts the monitor is skipped; set `OPEN_SWIM_SD_PATH` to point at the device mount when running without it.
- `sync_device_playlists()` copies normalized tracks onto the device:
  - Builds one folder per playlist using a sanitized title.
  - Computes a deterministic hash of ordered video ids; if unchanged compared to the playlist’s `sync.json` the copy is skipped.
  - Otherwise, wipes and recreates the playlist folder, copies MP3s from the local library, writes `sync.json` with metadata and the current hash, and reports progress to stdout.
- `OPEN_SWIM_SD_PATH` must point at the mounted device root for copying.

## Error handling and guarantees
- Sync work is serialized through a single queue to avoid overlapping downloads and device writes.
- External processes (ffmpeg, yt-dlp, Piper) run with `subprocess.run(..., check=True or error checks)`; failures raise and are logged by the worker loop, then the queue item is marked done to prevent deadlock.
- Podcasts and playlists are idempotent: presence in `info.json` (podcasts) or matching playlist hash (device sync) prevents duplicate work.

## Deployment notes
- Container images ship voice models from the Dockerfile `assets` stage and install `yt-dlp`, `piper-tts`, and dependencies into `/app/.venv`.
- `docker-compose.yml` demonstrates a privileged service that binds `/dev` and the `/mnt/openswim` mount, and points the MQTT broker at the host.

