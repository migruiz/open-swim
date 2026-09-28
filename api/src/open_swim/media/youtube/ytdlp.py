"""Run yt-dlp, updating it and retrying once when a call fails.

YouTube changes break yt-dlp every few weeks. docker-entrypoint.sh updates the
binary on start and nightly; this covers the gap in between, so a break during
the day heals itself on the next failed download instead of waiting for midnight.
"""

import subprocess
import threading
import time
from typing import List

from open_swim.config import config

# A failure for an unrelated reason (private or deleted video) must not turn
# every download into an update check.
UPDATE_COOLDOWN_SECONDS = 3600

_update_lock = threading.Lock()
_last_update_attempt: float | None = None


def _run(args: List[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [config.ytdlp_path, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def update_ytdlp() -> bool:
    """Update yt-dlp in place, at most once per cooldown.

    Returns True only when a newer version was installed, so the caller knows a
    retry could behave differently.
    """
    global _last_update_attempt
    with _update_lock:
        now = time.monotonic()
        if (
            _last_update_attempt is not None
            and now - _last_update_attempt < UPDATE_COOLDOWN_SECONDS
        ):
            return False
        _last_update_attempt = now

    channel = config.ytdlp_update_channel
    update_args = ["--update-to", channel] if channel else ["-U"]
    print(f"[yt-dlp] Call failed; checking for an update ({' '.join(update_args)})")
    try:
        result = _run(update_args, timeout=120)
    except Exception as exc:
        print(f"[yt-dlp] Update failed: {exc}")
        return False

    output = f"{result.stdout}\n{result.stderr}".strip()
    print(f"[yt-dlp] {output}")
    if result.returncode != 0:
        return False
    return "up to date" not in output.lower()


def run_ytdlp(args: List[str], timeout: int) -> subprocess.CompletedProcess[str]:
    """Run yt-dlp with args; on failure update it and retry once.

    Raises subprocess.TimeoutExpired like subprocess.run; timeouts are not retried.
    """
    result = _run(args, timeout)
    if result.returncode == 0:
        return result
    if update_ytdlp():
        print("[yt-dlp] Updated; retrying")
        return _run(args, timeout)
    return result
