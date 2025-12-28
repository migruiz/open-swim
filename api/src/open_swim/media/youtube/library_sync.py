import os
from pathlib import Path
import tempfile
from typing import List

from open_swim.messaging.models import SyncItemStatus, SyncPhase, SyncProgressMessage
from open_swim.messaging.progress import get_progress_reporter
from open_swim.media.youtube.download import download_audio
from open_swim.media.youtube.intro_processor import add_intro_to_video
from open_swim.media.youtube.library import (
    add_normalized_mp3_to_library,
    get_library_video_info,
    update_video_status,
)
from open_swim.media.youtube.models import PlaylistRequest, VideoStatus
from open_swim.media.youtube.normalize import get_normalized_loudness_file
from open_swim.media.youtube.playlists import PlaylistInfo, YoutubeVideo, fetch_playlist_information
from open_swim.media.youtube.playlists_to_sync import load_playlists_to_sync


def get_playlists_to_sync() -> List[PlaylistInfo]:
    """Return a list of playlist URLs to sync from requests saved on disk."""
    playlists_to_sync: List[PlaylistRequest] = load_playlists_to_sync()

    return [
        fetch_playlist_information(
            playlist_url=f"https://youtube.com/playlist?list={playlist.id.strip()}",
            playlist_title=playlist.title,
        )
        for playlist in playlists_to_sync
    ]


def _sync_video_to_library(
    video: YoutubeVideo,
    playlist_id: str,
    playlist_title: str,
    current_index: int,
    total_count: int,
) -> None:
    """Sync a single video to the library, downloading and normalizing if needed."""
    reporter = get_progress_reporter()
    library_video_info = get_library_video_info(video.id)
    if (
        library_video_info
        and library_video_info.status == VideoStatus.READY
        and library_video_info.mp3_path
        and os.path.exists(library_video_info.mp3_path)
    ):
        reporter.report_progress(
            SyncProgressMessage(
                phase=SyncPhase.youtube_library,
                status=SyncItemStatus.skipped,
                playlist_id=playlist_id,
                playlist_title=playlist_title,
                item_id=video.id,
                item_title=video.title,
                current_index=current_index,
                total_count=total_count,
            )
        )
        return

    print(f"[Library Sync] Processing video {video.title} - {video.id}...")
    try:
        reporter.report_progress(
            SyncProgressMessage(
                phase=SyncPhase.youtube_library,
                status=SyncItemStatus.downloading,
                playlist_id=playlist_id,
                playlist_title=playlist_title,
                item_id=video.id,
                item_title=video.title,
                current_index=current_index,
                total_count=total_count,
            )
        )
        update_video_status(video.id, VideoStatus.DOWNLOADING)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            temp_downloaded_mp3_path = download_audio(tmp_path=tmp_path, video_id=video.id)

            reporter.report_progress(
                SyncProgressMessage(
                    phase=SyncPhase.youtube_library,
                    status=SyncItemStatus.normalizing,
                    playlist_id=playlist_id,
                    playlist_title=playlist_title,
                    item_id=video.id,
                    item_title=video.title,
                    current_index=current_index,
                    total_count=total_count,
                )
            )
            update_video_status(video.id, VideoStatus.NORMALIZING)
            temp_normalized_mp3_path = get_normalized_loudness_file(
                tmp_path=tmp_path, mp3_file_path=temp_downloaded_mp3_path
            )

            update_video_status(video.id, VideoStatus.ADDING_INTRO)
            final_mp3_path = add_intro_to_video(
                video=video,
                normalized_mp3_path=temp_normalized_mp3_path,
                output_dir=tmp_path,
            )
            add_normalized_mp3_to_library(
                youtube_video=video,
                temp_normalized_mp3_path=final_mp3_path,
                playlist_id=playlist_id,
            )
            reporter.report_progress(
                SyncProgressMessage(
                    phase=SyncPhase.youtube_library,
                    status=SyncItemStatus.completed,
                    playlist_id=playlist_id,
                    playlist_title=playlist_title,
                    item_id=video.id,
                    item_title=video.title,
                    current_index=current_index,
                    total_count=total_count,
                )
            )
    except Exception as exc:
        update_video_status(video.id, VideoStatus.ERROR, str(exc))
        reporter.report_progress(
            SyncProgressMessage(
                phase=SyncPhase.youtube_library,
                status=SyncItemStatus.error,
                playlist_id=playlist_id,
                playlist_title=playlist_title,
                item_id=video.id,
                item_title=video.title,
                current_index=current_index,
                total_count=total_count,
                error_message=str(exc),
            )
        )
        raise


def _sync_library_playlist(playlist_info: PlaylistInfo) -> None:
    reporter = get_progress_reporter()
    total_videos = len(playlist_info.videos)
    reporter.report_progress(
        SyncProgressMessage(
            phase=SyncPhase.youtube_library,
            status=SyncItemStatus.started,
            playlist_id=playlist_info.id,
            playlist_title=playlist_info.title,
            total_count=total_videos,
        )
    )
    for index, video in enumerate(playlist_info.videos, start=1):
        try:
            _sync_video_to_library(
                video=video,
                playlist_id=playlist_info.id,
                playlist_title=playlist_info.title,
                current_index=index,
                total_count=total_videos,
            )
        except Exception as e:
            print(f"[Error] Failed to sync video {video.title} - {video.id}: {str(e)}")
    print(f"[Playlist] Extracted and processed {len(playlist_info.videos)} videos from playlist.")
    reporter.report_progress(
        SyncProgressMessage(
            phase=SyncPhase.youtube_library,
            status=SyncItemStatus.completed,
            playlist_id=playlist_info.id,
            playlist_title=playlist_info.title,
            current_index=total_videos,
            total_count=total_videos,
        )
    )


def sync_youtube_playlists_to_library(playlists_to_sync: List[PlaylistInfo]) -> None:
    """Sync all playlists specified in environment variable to the library."""
    for playlist in playlists_to_sync:
        print(f"[Playlist Sync] Syncing playlist: {playlist.title}")
        _sync_library_playlist(playlist)
