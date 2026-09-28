import subprocess
from typing import List

import pytest

from open_swim.media.youtube import ytdlp


def _result(returncode: int, stdout: str = "", stderr: str = "") -> "subprocess.CompletedProcess[str]":
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture(autouse=True)
def reset_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ytdlp, "_last_update_attempt", None)


class TestRunYtdlp:
    def test_success_does_not_update(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: List[List[str]] = []

        def fake_run(args: List[str], timeout: int) -> "subprocess.CompletedProcess[str]":
            calls.append(args)
            return _result(0, stdout="ok")

        monkeypatch.setattr(ytdlp, "_run", fake_run)

        assert ytdlp.run_ytdlp(["-x", "url"], timeout=5).stdout == "ok"
        assert calls == [["-x", "url"]]

    def test_failure_updates_and_retries_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: List[List[str]] = []
        outcomes = iter([_result(1, stderr="HTTP 403"), _result(0, stdout="ok")])

        def fake_run(args: List[str], timeout: int) -> "subprocess.CompletedProcess[str]":
            calls.append(args)
            return next(outcomes)

        monkeypatch.setattr(ytdlp, "_run", fake_run)
        monkeypatch.setattr(ytdlp, "update_ytdlp", lambda: True)

        assert ytdlp.run_ytdlp(["url"], timeout=5).returncode == 0
        assert calls == [["url"], ["url"]]

    def test_failure_without_new_version_does_not_retry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: List[List[str]] = []

        def fake_run(args: List[str], timeout: int) -> "subprocess.CompletedProcess[str]":
            calls.append(args)
            return _result(1, stderr="Video unavailable")

        monkeypatch.setattr(ytdlp, "_run", fake_run)
        monkeypatch.setattr(ytdlp, "update_ytdlp", lambda: False)

        assert ytdlp.run_ytdlp(["url"], timeout=5).returncode == 1
        assert len(calls) == 1


class TestUpdateYtdlp:
    def test_new_version_installed_returns_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            ytdlp, "_run", lambda args, timeout: _result(0, stdout="Updated yt-dlp to nightly@2026.09.27")
        )
        assert ytdlp.update_ytdlp() is True

    def test_already_up_to_date_returns_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            ytdlp, "_run", lambda args, timeout: _result(0, stdout="yt-dlp is up to date (nightly@2026.09.27)")
        )
        assert ytdlp.update_ytdlp() is False

    def test_second_attempt_within_cooldown_is_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: List[List[str]] = []

        def fake_run(args: List[str], timeout: int) -> "subprocess.CompletedProcess[str]":
            calls.append(args)
            return _result(0, stdout="Updated yt-dlp")

        monkeypatch.setattr(ytdlp, "_run", fake_run)

        assert ytdlp.update_ytdlp() is True
        assert ytdlp.update_ytdlp() is False
        assert len(calls) == 1
