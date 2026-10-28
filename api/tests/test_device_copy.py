import dataclasses
from pathlib import Path
from typing import Dict, List

import pytest

from open_swim.config import config
from open_swim.device.sync import files
from open_swim.device.sync.podcast import device_podcast_sync
from open_swim.device.sync.state import DevicePlaylistState, DeviceSyncState, load_sync_state, save_sync_state
from open_swim.device.sync.youtube import device_playlist_dirs_sync, device_youtube_sync
from open_swim.media.podcast.models import EpisodeRecord, EpisodeRequest, PodcastLibrary
from open_swim.media.youtube.models import VideoRecord, VideoStatus, YouTubeLibrary
from open_swim.media.youtube.playlists import PlaylistInfo, YoutubeVideo


class TestDeviceName:
    def test_superscript_and_accents_become_plain(self) -> None:
        name = "Harness²_Explained__normalized__pW2ktrJlsyE.mp3"
        assert files.device_name(name) == "Harness2_Explained__normalized__pW2ktrJlsyE.mp3"
        assert files.device_name("Música_ep1_001.mp3") == "Musica_ep1_001.mp3"

    def test_plain_name_is_unchanged(self) -> None:
        name = "AI_Writes_the_Code_-_Laurie_Voss__normalized__kspZP5BgkEU.mp3"
        assert files.device_name(name) == name

    def test_characters_fat_forbids_are_removed(self) -> None:
        assert files.device_name('a:b?c*"d.mp3') == "abcd.mp3"


def _library_with(tmp_path: Path, names: Dict[str, str]) -> YouTubeLibrary:
    videos = {}
    for video_id, filename in names.items():
        mp3 = tmp_path / "library" / filename
        mp3.parent.mkdir(exist_ok=True)
        mp3.write_bytes(video_id.encode())
        videos[video_id] = VideoRecord(
            id=video_id, title=video_id, status=VideoStatus.READY, mp3_path=str(mp3)
        )
    return YouTubeLibrary(videos=videos)


def _fail_on(monkeypatch: pytest.MonkeyPatch, module: object, bad_name: str) -> None:
    """Make copies to destinations ending in bad_name fail, as the Pi's FAT mount does."""
    real_copy = files.copy_file_to_device

    def copy(source: str, destination: str) -> None:
        if destination.endswith(bad_name):
            raise OSError(22, "Invalid argument", destination)
        real_copy(source, destination)

    monkeypatch.setattr(module, "copy_file_to_device", copy)


class TestPlaylistCopy:
    def _sync(self, tmp_path: Path, library: YouTubeLibrary) -> tuple[List[str], Dict[str, DevicePlaylistState]]:
        device = tmp_path / "device"
        device.mkdir()
        playlist = PlaylistInfo(
            id="PL",
            title="newai",
            videos=[YoutubeVideo(id=video_id, title=video_id) for video_id in ("a", "b", "c")],
        )
        state: Dict[str, DevicePlaylistState] = {}
        failures = device_youtube_sync._sync_playlist_to_device(
            playlist, library, str(device), state, current_index=1, total_count=1
        )
        return failures, state

    def test_names_on_the_device_are_plain_ascii(self, tmp_path: Path) -> None:
        library = _library_with(tmp_path, {"a": "a.mp3", "b": "Harness²_b.mp3", "c": "c.mp3"})

        failures, state = self._sync(tmp_path, library)

        assert failures == []
        copied = sorted(p.name for p in (tmp_path / "device" / "newai").iterdir())
        assert copied == ["Harness2_b.mp3", "a.mp3", "c.mp3"]
        assert state["PL"].playlist_hash is not None

    def test_one_failed_copy_does_not_stop_the_rest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        library = _library_with(tmp_path, {"a": "a.mp3", "b": "b.mp3", "c": "c.mp3"})
        _fail_on(monkeypatch, device_youtube_sync, "b.mp3")

        failures, state = self._sync(tmp_path, library)

        assert len(failures) == 1 and "b.mp3" in failures[0]
        copied = sorted(p.name for p in (tmp_path / "device" / "newai").iterdir())
        assert copied == ["a.mp3", "c.mp3"]
        # No hash, so the next sync tries the playlist again.
        assert state["PL"].playlist_hash is None


class TestRenamedPlaylistFolder:
    def test_renamed_folder_is_copied_again(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            device_playlist_dirs_sync, "config", dataclasses.replace(config, device_sd_path=str(tmp_path))
        )
        (tmp_path / "Música").mkdir()
        save_sync_state(
            DeviceSyncState(playlists=[DevicePlaylistState(id="PL", title="Música", playlist_hash="old")]),
            str(tmp_path),
        )

        device_playlist_dirs_sync.sync_playlists_directories([PlaylistInfo(id="PL", title="Música", videos=[])])

        playlists = load_sync_state(str(tmp_path)).playlists
        assert [(p.title, p.playlist_hash) for p in playlists] == [("Musica", None)]
        assert not (tmp_path / "Música").exists()


class TestPodcastCopy:
    def test_failed_episode_is_not_recorded_as_copied(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        device = tmp_path / "device"
        (device / "podcast").mkdir(parents=True)
        episodes = []
        records = {}
        for episode_id, date, segment in (("ok", "2026-05-11", "ok_001.mp3"), ("bad", "2026-05-12", "Música_001.mp3")):
            episode_dir = tmp_path / "library" / episode_id
            episode_dir.mkdir(parents=True)
            (episode_dir / segment).write_bytes(b"x")
            episodes.append(EpisodeRequest(id=episode_id, title=episode_id, date=date, download_url="http://x"))
            records[episode_id] = EpisodeRecord(
                id=episode_id, title=episode_id, date=date, episode_dir=str(episode_dir)
            )

        monkeypatch.setattr(
            device_podcast_sync, "config", dataclasses.replace(config, device_sd_path=str(device))
        )
        monkeypatch.setattr(device_podcast_sync, "load_episodes_to_sync", lambda: episodes)
        monkeypatch.setattr(device_podcast_sync.store, "load_library", lambda: PodcastLibrary(episodes=records))
        _fail_on(monkeypatch, device_podcast_sync, "Musica_001.mp3")

        with pytest.raises(RuntimeError, match="Could not copy 1 file"):
            device_podcast_sync.sync_podcast_episodes_to_device()

        assert sorted(p.name for p in (device / "podcast").iterdir()) == ["ok_001.mp3"]
        assert load_sync_state(str(device)).podcasts.synced_episode_ids == ["ok"]
