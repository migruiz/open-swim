import pytest

from open_swim.device.sync.youtube.sanitize import sanitize_playlist_title


class TestSanitizePlaylistTitle:
    def test_basic_title(self) -> None:
        assert sanitize_playlist_title("My Playlist") == "My_Playlist"

    def test_special_characters_removed(self) -> None:
        assert sanitize_playlist_title("Rock & Roll!") == "Rock__Roll"

    def test_multiple_spaces_collapsed(self) -> None:
        assert sanitize_playlist_title("Too   Many   Spaces") == "Too_Many_Spaces"

    def test_leading_trailing_spaces_stripped(self) -> None:
        assert sanitize_playlist_title("  Padded Title  ") == "Padded_Title"

    def test_empty_string_returns_default(self) -> None:
        assert sanitize_playlist_title("") == "playlist"

    def test_only_special_characters_returns_default(self) -> None:
        assert sanitize_playlist_title("!@#$%") == "playlist"

    def test_hyphens_preserved(self) -> None:
        assert sanitize_playlist_title("My-Playlist") == "My-Playlist"

    def test_underscores_preserved(self) -> None:
        assert sanitize_playlist_title("My_Playlist") == "My_Playlist"

    def test_unicode_letters_preserved(self) -> None:
        assert sanitize_playlist_title("Música") == "Música"

    def test_numbers_preserved(self) -> None:
        assert sanitize_playlist_title("Top 100 Hits") == "Top_100_Hits"
