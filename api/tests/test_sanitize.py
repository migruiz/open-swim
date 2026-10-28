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

    def test_accents_become_plain_letters(self) -> None:
        # The Pi's FAT mount rejects non-ASCII names.
        assert sanitize_playlist_title("Música") == "Musica"

    def test_superscript_becomes_plain_digit(self) -> None:
        assert sanitize_playlist_title("Harness² Explained") == "Harness2_Explained"

    def test_non_latin_title_falls_back_to_default(self) -> None:
        assert sanitize_playlist_title("音楽") == "playlist"

    def test_numbers_preserved(self) -> None:
        assert sanitize_playlist_title("Top 100 Hits") == "Top_100_Hits"
