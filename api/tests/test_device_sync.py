from pathlib import Path
from typing import List

import pytest

from open_swim.device.linux import monitor as linux_monitor
from open_swim.device.sync.podcast.device_podcast_sync import _episodes_ready_in_library
from open_swim.device.sync.youtube.device_youtube_sync import _videos_ready_in_library
from open_swim.media.podcast.models import EpisodeRecord, EpisodeRequest, PodcastLibrary
from open_swim.media.youtube.models import VideoRecord, VideoStatus, YouTubeLibrary
from open_swim.media.youtube.playlists import PlaylistInfo, YoutubeVideo, videos_to_sync


def _playlist(count: int) -> PlaylistInfo:
    return PlaylistInfo(
        id="PL",
        title="pl",
        videos=[YoutubeVideo(id=f"v{i}", title=f"v{i}") for i in range(count)],
    )


class TestVideosToSync:
    def test_newest_first_and_capped(self) -> None:
        # YouTube lists oldest-added first, so the newest are at the end.
        ids = [video.id for video in videos_to_sync(_playlist(25))]

        assert ids[:3] == ["v24", "v23", "v22"]
        assert len(ids) == 20

    def test_short_playlist_is_not_padded(self) -> None:
        assert len(videos_to_sync(_playlist(3))) == 3


class TestVideosReadyInLibrary:
    def test_only_videos_with_an_existing_mp3_are_ready(self, tmp_path: Path) -> None:
        present = tmp_path / "a.mp3"
        present.write_bytes(b"a")
        library = YouTubeLibrary(
            videos={
                "a": VideoRecord(id="a", title="a", status=VideoStatus.READY, mp3_path=str(present)),
                "b": VideoRecord(id="b", title="b", status=VideoStatus.DOWNLOADING),
                "c": VideoRecord(
                    id="c", title="c", status=VideoStatus.READY, mp3_path=str(tmp_path / "gone.mp3")
                ),
            }
        )
        videos = [YoutubeVideo(id=i, title=i) for i in ("a", "b", "c", "d")]

        ready = _videos_ready_in_library(videos, library)

        assert [(video.id, path) for video, path in ready] == [("a", str(present))]


class TestEpisodesReadyInLibrary:
    def test_episode_still_downloading_is_not_ready(self, tmp_path: Path) -> None:
        done_dir = tmp_path / "done"
        done_dir.mkdir()
        library = PodcastLibrary(
            episodes={
                "done": EpisodeRecord(id="done", title="d", date="2026-09-01", episode_dir=str(done_dir)),
                "busy": EpisodeRecord(id="busy", title="b", date="2026-09-02"),
            }
        )
        requests = [
            EpisodeRequest(id=i, title=i, date="2026-09-01", download_url="http://x")
            for i in ("done", "busy", "new")
        ]

        ready = _episodes_ready_in_library(requests, library)

        assert [(episode.id, path) for episode, path in ready] == [("done", str(done_dir))]


class TestLinuxMonitorMounting:
    @pytest.fixture
    def monitor(self, monkeypatch: pytest.MonkeyPatch) -> linux_monitor.LinuxDeviceMonitor:
        self.mounted_paths: List[str] = []
        self.unmounts: List[str] = []
        self.is_mount = False

        def fake_mount(dev: str, mount_point: str) -> bool:
            self.mounted_paths.append(dev)
            self.is_mount = True
            return True

        def fake_unmount(mount_point: str, lazy_fallback: bool = False) -> bool:
            self.unmounts.append(mount_point)
            self.is_mount = False
            return True

        monkeypatch.setattr(linux_monitor, "mount_volume", fake_mount)
        monkeypatch.setattr(linux_monitor, "unmount_volume", fake_unmount)
        monkeypatch.setattr(linux_monitor.os.path, "ismount", lambda path: self.is_mount)
        monkeypatch.setattr(linux_monitor.os, "sync", lambda: None, raising=False)

        m = linux_monitor.LinuxDeviceMonitor(
            on_connected=lambda monitor, device, mount_point: None,
            on_disconnected=lambda monitor: None,
        )
        m.connected = True
        m.current_dev = "/dev/sda1"
        return m

    def test_mounts_on_demand_and_releases_after(self, monitor: linux_monitor.LinuxDeviceMonitor) -> None:
        assert monitor.ensure_mounted() is True
        assert monitor.ensure_mounted() is True  # already mounted: no second mount
        assert self.mounted_paths == ["/dev/sda1"]

        assert monitor.release() is True
        assert monitor.mounted is False
        assert len(self.unmounts) == 1

    def test_mount_that_does_not_take_is_not_trusted(
        self, monitor: linux_monitor.LinuxDeviceMonitor, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(linux_monitor, "mount_volume", lambda dev, mount_point: True)

        assert monitor.ensure_mounted() is False

    def test_disconnected_device_is_not_mounted_or_released(
        self, monitor: linux_monitor.LinuxDeviceMonitor
    ) -> None:
        monitor.connected = False

        assert monitor.ensure_mounted() is False
        assert monitor.release() is False
        assert self.mounted_paths == []
