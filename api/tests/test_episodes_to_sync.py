from open_swim.media.podcast.episodes_to_sync import _convert_json_to_episode_list, episodes_to_sync_response
from open_swim.media.podcast.models import EpisodeRecord, EpisodeStatus, PodcastLibrary


def test_start_part_defaults_to_the_first_part() -> None:
    payload = '[{"id": "a", "date": "2026-05-11", "title": "A", "download_url": "http://x"}]'

    assert _convert_json_to_episode_list(payload)[0].start_part == 1


def test_response_carries_start_part_and_part_count_once_split() -> None:
    episodes = _convert_json_to_episode_list(
        '[{"id": "a", "date": "2026-05-11", "title": "A", "download_url": "http://x", "start_part": 4},'
        ' {"id": "b", "date": "2026-05-12", "title": "B", "download_url": "http://y"}]'
    )
    library = PodcastLibrary(
        episodes={
            "a": EpisodeRecord(id="a", title="A", date="2026-05-11", status=EpisodeStatus.READY, segment_count=18),
            "b": EpisodeRecord(id="b", title="B", date="2026-05-12", status=EpisodeStatus.SEGMENTING),
        }
    )

    response = episodes_to_sync_response(episodes, library)

    assert [(r["id"], r["start_part"], r["part_count"]) for r in response] == [("a", 4, 18), ("b", 1, None)]
