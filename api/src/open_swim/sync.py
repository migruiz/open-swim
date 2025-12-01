
import queue
import threading
from typing import Callable
from open_swim.device.device_youtube_sync import sync_device_playlists
from open_swim.media.podcast.sync import sync_podcast_episodes
from open_swim.media.youtube.library_sync import get_playlists_to_sync, sync_youtube_playlists_to_library

_sync_task_queue: queue.Queue[Callable[[], None]] = queue.Queue()


def _sync_worker() -> None:
    """Process sync jobs sequentially to avoid concurrent runs."""
    while True:
        task = _sync_task_queue.get()
        try:
            task()
        except Exception as exc:  # pragma: no cover - best effort logging only
            print(f"Podcast sync task failed: {exc}")
        finally:
            _sync_task_queue.task_done()


threading.Thread(target=_sync_worker, daemon=True).start()


def work() -> None:
    sync_podcast_episodes()
    playlists_to_sync = get_playlists_to_sync()
    sync_youtube_playlists_to_library(playlists_to_sync)
    sync_device_playlists(play_lists=playlists_to_sync)


def enqueue_sync() -> None:
    """Enqueue a sync job so only one runs at a time."""
    _sync_task_queue.put(work)
