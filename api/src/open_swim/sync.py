import queue
import threading
import time
from typing import Callable, List, Optional

from open_swim.config import config
from open_swim.media.podcast.sync import sync_podcast_episodes
from open_swim.media.prune import prune_podcasts, prune_youtube
from open_swim.media.youtube.library_sync import get_playlists_to_sync, sync_youtube_playlists_to_library
from open_swim.device.sync.youtube.device_youtube_sync import sync_device_playlists_videos
from open_swim.device.sync.youtube.device_playlist_dirs_sync import sync_playlists_directories
from open_swim.device.sync.podcast.device_podcast_dirs_sync import create_podcast_folder
from open_swim.device.sync.podcast.device_podcast_sync import sync_podcast_episodes_to_device
from open_swim.media.youtube.playlists import PlaylistInfo
from open_swim.messaging.models import StageStatus, SyncStage, SyncProgressMessage
from open_swim.messaging.progress import get_progress_reporter


_sync_task_queue: queue.Queue[Callable[[], None]] = queue.Queue()

# Guards _sync_pending and _selection_timer.
_schedule_lock = threading.Lock()
# True while a sync sits in the queue waiting to start. Triggers arriving then
# (plug-in, timer, MQTT reconnect) are already covered by it and are dropped.
_sync_pending = False
_selection_timer: Optional[threading.Timer] = None


def _sync_worker() -> None:
    """Process sync jobs sequentially to avoid concurrent runs."""
    while True:
        task = _sync_task_queue.get()
        try:
            task()
        except Exception as exc:  # pragma: no cover - best effort logging only
            print(f"Sync task failed: {exc}")
            import traceback
            traceback.print_exc()
        finally:
            _sync_task_queue.task_done()


threading.Thread(target=_sync_worker, daemon=True).start()


def _report_stages(stages: List[SyncStage]) -> None:
    reporter = get_progress_reporter()
    reporter.report_progress(SyncProgressMessage(stages=list(stages)))


def _prune(label: str, prune: Callable[[], None]) -> None:
    """Run a library prune if enabled; a failure here must not fail the sync."""
    if not config.library_prune:
        return
    try:
        prune()
    except Exception as exc:
        print(f"[Prune] Failed to prune {label} library: {exc}")


def work() -> None:
    stages: List[SyncStage] = []
    playlists_to_sync: List[PlaylistInfo] = []

    # Stage 1: Podcast Library
    stage1 = SyncStage(
        name="podcast_library",
        label="Download podcast episodes",
        status=StageStatus.running,
    )
    stages.append(stage1)
    _report_stages(stages)
    try:
        sync_podcast_episodes()
        stage1.status = StageStatus.completed
    except Exception as e:
        stage1.status = StageStatus.error
        stage1.error = str(e)
    _report_stages(stages)
    _prune("podcast", prune_podcasts)

    # Stage 2: YouTube Library
    stage2 = SyncStage(
        name="youtube_library",
        label="Download YouTube playlists",
        status=StageStatus.running,
    )
    stages.append(stage2)
    _report_stages(stages)
    youtube_library_ok = False
    try:
        playlists_to_sync = get_playlists_to_sync()
        sync_youtube_playlists_to_library(playlists_to_sync)
        stage2.status = StageStatus.completed
        youtube_library_ok = True
    except Exception as e:
        stage2.status = StageStatus.error
        stage2.error = str(e)
    _report_stages(stages)
    # Same guard as stage 3: without a successful fetch, playlists_to_sync is
    # empty and would read as "keep nothing".
    if youtube_library_ok:
        _prune("YouTube", lambda: prune_youtube(playlists_to_sync))

    # Check device connection
    from open_swim.app import get_device_monitor, release_device
    device_monitor = get_device_monitor()
    if device_monitor is None or not device_monitor.connected:
        print("[SYNC] Skipping device sync: device not connected")
        return
    if not device_monitor.ensure_mounted():
        print("[SYNC] Skipping device sync: could not mount device")
        return

    try:
        _copy_to_device(stages, playlists_to_sync, youtube_library_ok)
    finally:
        # Flush and unmount after every copy, so the player can be pulled out
        # at any time between syncs without risking its filesystem.
        release_device()


def _copy_to_device(
    stages: List[SyncStage],
    playlists_to_sync: List[PlaylistInfo],
    youtube_library_ok: bool,
) -> None:
    # Stage 3: Device YouTube
    # Only run when the library stage succeeded. On failure `playlists_to_sync`
    # is still the empty list it was initialized to, and syncing that would read
    # as "no playlists requested" and delete every playlist folder on the device.
    if not youtube_library_ok:
        print("[SYNC] Skipping device YouTube sync: YouTube library stage failed")
    else:
        stage3 = SyncStage(
            name="device_youtube",
            label="Copy YouTube to device",
            status=StageStatus.running,
        )
        stages.append(stage3)
        _report_stages(stages)
        try:
            sync_playlists_directories(playlists_to_sync)
            sync_device_playlists_videos(play_lists=playlists_to_sync)
            stage3.status = StageStatus.completed
        except Exception as e:
            stage3.status = StageStatus.error
            stage3.error = str(e)
        _report_stages(stages)

    # Stage 4: Device Podcast
    stage4 = SyncStage(
        name="device_podcast",
        label="Copy podcasts to device",
        status=StageStatus.running,
    )
    stages.append(stage4)
    _report_stages(stages)
    try:
        create_podcast_folder()
        sync_podcast_episodes_to_device()
        stage4.status = StageStatus.completed
    except Exception as e:
        stage4.status = StageStatus.error
        stage4.error = str(e)
    _report_stages(stages)


def _run_queued_sync() -> None:
    global _sync_pending
    with _schedule_lock:
        _sync_pending = False
    work()


def enqueue_sync() -> None:
    """Queue a sync so only one runs at a time.

    At most one sync waits behind the running one: it starts after the current
    run and picks up everything that changed meanwhile, so further triggers are
    redundant.
    """
    global _sync_pending
    with _schedule_lock:
        if _sync_pending:
            print("[SYNC] A sync is already queued; not adding another")
            return
        _sync_pending = True
    _sync_task_queue.put(_run_queued_sync)


def enqueue_sync_after_quiet_period(delay_seconds: Optional[float] = None) -> None:
    """Queue a sync once selections have stopped changing for delay_seconds.

    Each call restarts the wait, so ticking several episodes one after another
    starts a single sync after the last tick rather than one per tick.
    """
    global _selection_timer
    delay = config.selection_sync_delay_seconds if delay_seconds is None else delay_seconds
    with _schedule_lock:
        if _selection_timer is not None:
            _selection_timer.cancel()
        _selection_timer = threading.Timer(delay, enqueue_sync)
        _selection_timer.daemon = True
        _selection_timer.start()
    print(f"[SYNC] Selection changed; syncing in {delay:.0f}s unless it changes again")


def start_periodic_sync(interval_hours: Optional[float] = None) -> None:
    """Queue a sync every interval_hours in the background; 0 disables it.

    Unplugged, this keeps the library downloaded ahead of time so plugging in
    only has to copy. Plugged in, it picks up videos added since the last sync.
    """
    hours = config.sync_interval_hours if interval_hours is None else interval_hours
    if hours <= 0:
        print("[SYNC] Periodic sync disabled")
        return

    def _loop() -> None:
        while True:
            time.sleep(hours * 3600)
            enqueue_sync()

    threading.Thread(target=_loop, daemon=True).start()
    print(f"[SYNC] Periodic sync every {hours:g}h")
