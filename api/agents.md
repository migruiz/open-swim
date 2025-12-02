# Agents Guide

Quick orientation for anyone (or any AI assistant) working on this repository.

- **What this service does:** Long-running MQTT worker that normalizes YouTube playlists and podcast episodes into `LIBRARY_PATH`, then mirrors playlists onto an OpenSwim device via a hashed, folder-per-playlist copy.
- **Primary code paths:** `src/open_swim/app.py` (entry + MQTT/device wiring), `src/open_swim/sync.py` (queue + orchestrator), `src/open_swim/media/youtube/*` (download, normalize, playlist handling), `src/open_swim/media/podcast/*` (download, split, intros), `src/open_swim/device/*` (mounting + sync).
- **Key commands**
  - Install deps: `uv sync`
  - Run service: `uv run open-swim`
  - One-off sync (skips MQTT/device monitor): `uv run python - <<'PY'\nfrom open_swim.sync import work\nwork()\nPY`
- **Side effects to be mindful of**
  - Download-heavy steps (yt-dlp, Piper, ffmpeg) will trigger network and CPU usage; avoid running during code review or unless needed.
  - `DeviceMonitor` is Linux-specific and will attempt to mount `/dev/sd*`; on non-Linux platforms set `OPEN_SWIM_SD_PATH` and avoid invoking monitor/eject flows.
  - Syncing to a device removes and recreates playlist folders before copying; ensure `OPEN_SWIM_SD_PATH` points at test media when experimenting.
- **Debug tips**
  - Library state lives under `LIBRARY_PATH` (default `/library`) with `info.json` files for both podcasts and YouTube; deleting those clears cached knowledge.
  - MQTT contract is in `README.md`; simulate messages by publishing to `openswim/episodes_to_sync` or `openswim/playlists_to_sync` with JSON payloads.
- **Coding norms**
  - Prefer `apply_patch` for edits, keep code ASCII, add concise comments only where behavior is non-obvious, and preserve user changes.
