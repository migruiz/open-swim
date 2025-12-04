
import queue
import threading
from typing import Callable, Optional, TYPE_CHECKING

from open_swim.media.podcast.sync import sync_podcast_episodes
from open_swim.media.youtube.library_sync import get_playlists_to_sync, sync_youtube_playlists_to_library
from open_swim.device.sync.device_sync import sync_device

if TYPE_CHECKING:
    from open_swim.device.monitor import DeviceMonitor

_sync_task_queue: queue.Queue[Callable[[], None]] = queue.Queue()
_device_monitor: Optional["DeviceMonitor"] = None


def set_device_monitor(monitor: "DeviceMonitor") -> None:
    """Set the device monitor reference for connection checks."""
    global _device_monitor
    _device_monitor = monitor


def _sync_worker() -> None:
    """Process sync jobs sequentially to avoid concurrent runs."""
    while True:
        task = _sync_task_queue.get()
        try:
            task()
        except Exception as exc:  # pragma: no cover - best effort logging only
            print(f"Podcast sync task failed: {exc}")
            #print the stack trace
            import traceback
            traceback.print_exc()
        finally:
            _sync_task_queue.task_done()


threading.Thread(target=_sync_worker, daemon=True).start()


def work() -> None:
    sync_podcast_episodes()

    playlists_to_sync = get_playlists_to_sync()
    sync_youtube_playlists_to_library(playlists_to_sync)

    if _device_monitor is None or not _device_monitor.connected:
        print("[SYNC] Skipping device sync: device not connected")
        return

    sync_device(playlists_to_sync)



def enqueue_sync() -> None:
    """Enqueue a sync job so only one runs at a time."""
    _sync_task_queue.put(work)
