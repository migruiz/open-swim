
import queue
import threading
from typing import Callable, List

from open_swim.media.podcast.sync import sync_podcast_episodes
from open_swim.media.youtube.library_sync import get_playlists_to_sync, sync_youtube_playlists_to_library
from open_swim.device.sync.youtube.device_youtube_sync import sync_device_playlists_videos
from open_swim.device.sync.youtube.device_playlist_dirs_sync import sync_playlists_directories
from open_swim.device.sync.podcast.device_podcast_dirs_sync import create_podcast_folder
from open_swim.device.sync.podcast.device_podcast_sync import sync_podcast_episodes_to_device
from open_swim.media.youtube.playlists import PlaylistInfo
from open_swim.messaging.models import StageStatus, SyncStage, SyncProgressMessage
from open_swim.messaging.progress import get_progress_reporter


_sync_task_queue: queue.Queue[Callable[[], None]] = queue.Queue()


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

    # Check device connection
    from open_swim.app import get_device_monitor
    device_monitor = get_device_monitor()
    if device_monitor is None or not device_monitor.connected:
        print("[SYNC] Skipping device sync: device not connected")
        return

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


def enqueue_sync() -> None:
    """Enqueue a sync job so only one runs at a time."""
    _sync_task_queue.put(work)
