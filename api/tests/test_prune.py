from pathlib import Path

from open_swim.media.podcast.models import EpisodeRecord, EpisodeStatus, PodcastLibrary
from open_swim.media.prune import prune_podcast_library, prune_youtube_library
from open_swim.media.youtube.models import VideoRecord, VideoStatus, YouTubeLibrary


def _video(video_id: str, mp3_path: str | None) -> VideoRecord:
    return VideoRecord(id=video_id, title=video_id, status=VideoStatus.READY, mp3_path=mp3_path)


def _episode(episode_id: str, episode_dir: str | None) -> EpisodeRecord:
    return EpisodeRecord(
        id=episode_id,
        title=episode_id,
        date="2026-09-01",
        status=EpisodeStatus.READY,
        episode_dir=episode_dir,
    )


class TestPruneYoutubeLibrary:
    def test_removes_unselected_videos_and_their_files(self, tmp_path: Path) -> None:
        keep = tmp_path / "keep.mp3"
        drop = tmp_path / "drop.mp3"
        keep.write_bytes(b"k")
        drop.write_bytes(b"d")
        library = YouTubeLibrary(
            videos={"keep": _video("keep", str(keep)), "drop": _video("drop", str(drop))}
        )

        removed = prune_youtube_library(library, {"keep"}, str(tmp_path))

        assert removed == ["drop"]
        assert set(library.videos) == {"keep"}
        assert keep.exists()
        assert not drop.exists()

    def test_never_deletes_files_outside_the_library(self, tmp_path: Path) -> None:
        library_dir = tmp_path / "library"
        library_dir.mkdir()
        outside = tmp_path / "outside.mp3"
        outside.write_bytes(b"o")
        library = YouTubeLibrary(videos={"x": _video("x", str(outside))})

        removed = prune_youtube_library(library, set(), str(library_dir))

        assert removed == ["x"]
        assert outside.exists()

    def test_drops_records_whose_file_is_already_gone(self, tmp_path: Path) -> None:
        library = YouTubeLibrary(
            videos={"gone": _video("gone", str(tmp_path / "gone.mp3")), "none": _video("none", None)}
        )

        removed = prune_youtube_library(library, set(), str(tmp_path))

        assert sorted(removed) == ["gone", "none"]
        assert library.videos == {}


class TestPrunePodcastLibrary:
    def test_removes_unselected_episode_folders(self, tmp_path: Path) -> None:
        keep_dir = tmp_path / "keep"
        drop_dir = tmp_path / "drop"
        for folder in (keep_dir, drop_dir):
            folder.mkdir()
            (folder / "001.mp3").write_bytes(b"s")
        library = PodcastLibrary(
            episodes={"keep": _episode("keep", str(keep_dir)), "drop": _episode("drop", str(drop_dir))}
        )

        removed = prune_podcast_library(library, {"keep"}, str(tmp_path))

        assert removed == ["drop"]
        assert keep_dir.exists()
        assert not drop_dir.exists()

    def test_never_deletes_the_library_folder_itself(self, tmp_path: Path) -> None:
        (tmp_path / "info.json").write_text("{}")
        library = PodcastLibrary(episodes={"bad": _episode("bad", str(tmp_path))})

        prune_podcast_library(library, set(), str(tmp_path))

        assert (tmp_path / "info.json").exists()
