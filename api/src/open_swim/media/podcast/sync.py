import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import List

import requests

from open_swim.config import config
from open_swim.media.podcast.episode_processor import get_episode_segments
from open_swim.media.podcast.episodes_to_sync import load_episodes_to_sync
from open_swim.messaging.models import SyncItemStatus, SyncPhase, SyncProgressMessage
from open_swim.messaging.progress import get_progress_reporter
from open_swim.media.podcast.models import (
    EpisodeRecord,
    EpisodeRequest,
    EpisodeStatus,
    PodcastLibrary,
)
from open_swim.media.podcast import store


def sync_podcast_episodes() -> None:
    """Sync multiple podcast episodes by processing each one."""
    episodes = load_episodes_to_sync()
    total = len(episodes)
    for index, episode in enumerate(episodes, start=1):
        _process_podcast_episode(episode=episode, current_index=index, total_count=total)


def _process_podcast_episode(
    episode: EpisodeRequest, current_index: int, total_count: int
) -> None:
    """Process a podcast episode by downloading, splitting, adding intros, and merging segments."""
    reporter = get_progress_reporter()
    library_info = store.load_library()
    existing = library_info.episodes.get(episode.id)
    if (
        existing
        and existing.status == EpisodeStatus.READY
        and existing.episode_dir
        and os.path.exists(existing.episode_dir)
    ):
        print(f"Episode {episode.id} already processed. Skipping.")
        reporter.report_progress(
            SyncProgressMessage(
                phase=SyncPhase.podcast_library,
                status=SyncItemStatus.skipped,
                item_id=episode.id,
                item_title=episode.title,
                current_index=current_index,
                total_count=total_count,
            )
        )
        return

    try:
        reporter.report_progress(
            SyncProgressMessage(
                phase=SyncPhase.podcast_library,
                status=SyncItemStatus.downloading,
                item_id=episode.id,
                item_title=episode.title,
                current_index=current_index,
                total_count=total_count,
            )
        )
        _upsert_episode_record(library_info, episode, status=EpisodeStatus.DOWNLOADING)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            print(f"Downloading podcast from {episode.download_url}...")
            episode_path = _download_podcast(url=episode.download_url, output_dir=tmp_path)

            reporter.report_progress(
                SyncProgressMessage(
                    phase=SyncPhase.podcast_library,
                    status=SyncItemStatus.segmenting,
                    item_id=episode.id,
                    item_title=episode.title,
                    current_index=current_index,
                    total_count=total_count,
                )
            )
            _upsert_episode_record(library_info, episode, status=EpisodeStatus.SEGMENTING)

            final_segments = get_episode_segments(
                episode=episode,
                episode_path=episode_path,
                tmp_path=tmp_path,
            )

            episode_dir = _get_library_episode_directory(episode)
            _copy_episode_segments_to_library(
                episode_dir=episode_dir, segments_paths=final_segments
            )

            _upsert_episode_record(
                library_info,
                episode,
                status=EpisodeStatus.READY,
                episode_dir=str(episode_dir),
                segment_count=len(final_segments),
            )
            print(f"Processing complete! Generated {len(final_segments)} segments.")
            reporter.report_progress(
                SyncProgressMessage(
                    phase=SyncPhase.podcast_library,
                    status=SyncItemStatus.completed,
                    item_id=episode.id,
                    item_title=episode.title,
                    current_index=current_index,
                    total_count=total_count,
                )
            )
    except Exception as exc:
        print(f"[Error] Failed to sync episode {episode.title} - {episode.id}: {exc}")
        _upsert_episode_record(library_info, episode, status=EpisodeStatus.ERROR, error_message=str(exc))
        reporter.report_progress(
            SyncProgressMessage(
                phase=SyncPhase.podcast_library,
                status=SyncItemStatus.error,
                item_id=episode.id,
                item_title=episode.title,
                current_index=current_index,
                total_count=total_count,
                error_message=str(exc),
            )
        )


def _upsert_episode_record(
    library_info: PodcastLibrary,
    episode: EpisodeRequest,
    status: EpisodeStatus,
    episode_dir: str | None = None,
    segment_count: int | None = None,
    error_message: str | None = None,
) -> None:
    """Update or create an episode record with the given status."""
    record = library_info.episodes.get(episode.id) or EpisodeRecord(
        id=episode.id,
        title=episode.title,
        date=episode.date,
        status=status,
        episode_dir=episode_dir,
        segment_count=segment_count,
        error_message=error_message,
    )
    record.status = status
    record.error_message = error_message
    if episode_dir:
        record.episode_dir = episode_dir
    if segment_count is not None:
        record.segment_count = segment_count
    library_info.episodes[episode.id] = record
    store.save_library(library_info)


def _get_library_episode_directory(episode: EpisodeRequest) -> Path:
    episode_folder = episode.title + "_" + episode.id
    episode_folder = re.sub(r"[^\w\s-]", "", episode_folder)
    episode_folder = re.sub(r"[\s]+", "_", episode_folder.strip())
    episode_dir = Path(config.podcasts_library_path) / episode_folder
    return episode_dir


def _copy_episode_segments_to_library(episode_dir: Path, segments_paths: List[Path]) -> None:
    episode_dir.mkdir(parents=True, exist_ok=True)
    for segment_path in segments_paths:
        destination = episode_dir / segment_path.name
        shutil.copy2(segment_path, destination)


def _download_podcast(url: str, output_dir: Path) -> Path:
    """Download podcast from the given URL.
    Returns the path to the downloaded file."""

    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()

    filename = (url.split("/")[-1] or "podcast.mp3")[:18]
    if not filename.endswith(".mp3"):
        filename += ".mp3"

    output_path = output_dir / filename

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return output_path
