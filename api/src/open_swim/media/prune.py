"""Remove library files that are no longer selected (enabled by LIBRARY_PRUNE).

Without this the library only grows: every video that ever sat in a playlist's
newest N and every podcast episode ever ticked stays on disk, which a Raspberry
Pi's SD card cannot absorb for long.
"""

import os
import shutil
from typing import List, Set

from open_swim.config import config
from open_swim.media.podcast import store as podcast_store
from open_swim.media.podcast.models import PodcastLibrary
from open_swim.media.youtube import store as youtube_store
from open_swim.media.youtube.models import YouTubeLibrary
from open_swim.media.youtube.playlists import PlaylistInfo, videos_to_sync


def _is_inside(path: str, root: str) -> bool:
    """True when path resolves to a location under root."""
    try:
        real_root = os.path.realpath(root)
        return os.path.commonpath([os.path.realpath(path), real_root]) == real_root
    except ValueError:  # different drives on Windows
        return False


def prune_youtube_library(
    library: YouTubeLibrary, keep_ids: Set[str], library_dir: str
) -> List[str]:
    """Drop records not in keep_ids and delete their MP3s. Returns removed ids.

    Files outside library_dir are never deleted; only their record is dropped.
    """
    removed: List[str] = []
    for video_id in list(library.videos):
        if video_id in keep_ids:
            continue
        record = library.videos.pop(video_id)
        path = record.mp3_path
        if path and _is_inside(path, library_dir) and os.path.isfile(path):
            os.remove(path)
        removed.append(video_id)
    return removed


def prune_podcast_library(
    library: PodcastLibrary, keep_ids: Set[str], library_dir: str
) -> List[str]:
    """Drop episode records not in keep_ids and delete their segment folders.

    Folders outside library_dir, or the library folder itself, are never deleted.
    """
    removed: List[str] = []
    real_library_dir = os.path.realpath(library_dir)
    for episode_id in list(library.episodes):
        if episode_id in keep_ids:
            continue
        record = library.episodes.pop(episode_id)
        path = record.episode_dir
        if (
            path
            and _is_inside(path, library_dir)
            and os.path.realpath(path) != real_library_dir
            and os.path.isdir(path)
        ):
            shutil.rmtree(path)
        removed.append(episode_id)
    return removed


def prune_youtube(playlists: List[PlaylistInfo]) -> None:
    """Delete library videos outside every playlist's newest N."""
    keep_ids = {video.id for playlist in playlists for video in videos_to_sync(playlist)}
    # An empty selection is more likely a lost or misread playlist list than a
    # real request to delete everything, so do nothing.
    if not keep_ids:
        print("[Prune] No playlist videos selected; not pruning the YouTube library")
        return
    library = youtube_store.load_library()
    removed = prune_youtube_library(library, keep_ids, config.youtube_library_path)
    if removed:
        youtube_store.save_library(library)
        print(f"[Prune] Removed {len(removed)} YouTube videos no longer in any playlist")


def prune_podcasts() -> None:
    """Delete processed podcast episodes that are no longer selected."""
    keep_ids = {episode.id for episode in podcast_store.load_episode_requests()}
    if not keep_ids:
        print("[Prune] No podcast episodes selected; not pruning the podcast library")
        return
    library = podcast_store.load_library()
    removed = prune_podcast_library(library, keep_ids, config.podcasts_library_path)
    if removed:
        podcast_store.save_library(library)
        print(f"[Prune] Removed {len(removed)} podcast episodes no longer selected")
