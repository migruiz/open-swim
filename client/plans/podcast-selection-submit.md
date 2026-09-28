# App: confirm podcast picks with a Submit button

Status: **done** (2026-09-28). Picks now live in `SelectionController`; edits are sent with a Submit button, confirmed by the Pi, and the app shows player status and the last sync. The notes below are kept for context.

## Problem

`_onEpisodeToggled` in `lib/screens/home_screen.dart` calls `_publishSyncList()` on every tick, so each tap sends the whole selection to `openswim/episodes_to_sync`.

The Pi now starts a download when a selection arrives. Miguel does not want a download to start on every tap. The goal is to pick several episodes, then confirm.

## What the server does now (stopgap)

`enqueue_sync_after_quiet_period()` in `api/src/open_swim/sync.py` waits `SELECTION_SYNC_DELAY_SECONDS` (default 120) after the *last* selection message before syncing. Each new message restarts the wait. So taps spaced less than two minutes apart start a single sync.

## Wanted in the app

- Ticking episodes only changes local state and marks the list as having unsent changes. Show a count, e.g. "3 changes".
- A **Submit** (or "Sync these") button publishes the full list once. Keep the existing payload: the whole selection, not a diff.
- Disable the button, or warn, while MQTT is disconnected. Published messages are not retained, so a pick sent while the Pi is offline is lost.
- Once the app confirms, the server delay can drop (e.g. `SELECTION_SYNC_DELAY_SECONDS=10`) so downloads start almost immediately.

## Related app work (optional, same session)

- Show the player status from the retained `openswim/device/status` topic. It is now `connected` → `safe_to_unplug` → `disconnected`. "Safe to unplug" is the morning signal that the overnight sync finished.
- Show the last sync result from `openswim/sync/progress` (stages with completed/error).
- The YouTube tab is still a placeholder. Playlists are set by publishing `[{id, title}]` to `openswim/playlists_to_sync`.
