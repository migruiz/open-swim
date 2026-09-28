import queue
import threading
from typing import List

import pytest

from open_swim import sync


@pytest.fixture
def fresh_queue(monkeypatch: pytest.MonkeyPatch) -> "queue.Queue[object]":
    # The module's worker thread stays blocked on the original queue, so jobs put
    # on this one are only run when a test runs them.
    q: "queue.Queue[object]" = queue.Queue()
    monkeypatch.setattr(sync, "_sync_task_queue", q)
    monkeypatch.setattr(sync, "_sync_pending", False)
    return q


class TestEnqueueSync:
    def test_second_trigger_while_one_is_waiting_is_dropped(self, fresh_queue: "queue.Queue[object]") -> None:
        sync.enqueue_sync()
        sync.enqueue_sync()
        sync.enqueue_sync()

        assert fresh_queue.qsize() == 1

    def test_can_queue_again_once_the_waiting_sync_starts(
        self, fresh_queue: "queue.Queue[object]", monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runs: List[int] = []
        monkeypatch.setattr(sync, "work", lambda: runs.append(1))

        sync.enqueue_sync()
        job = fresh_queue.get_nowait()
        job()  # type: ignore[operator]
        sync.enqueue_sync()

        assert runs == [1]
        assert fresh_queue.qsize() == 1


class TestEnqueueSyncAfterQuietPeriod:
    def test_rapid_changes_start_a_single_sync(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fired = threading.Event()
        calls: List[int] = []

        def fake_enqueue() -> None:
            calls.append(1)
            fired.set()

        monkeypatch.setattr(sync, "enqueue_sync", fake_enqueue)
        # threading.Timer looks enqueue_sync up when the timer is created.
        monkeypatch.setattr(sync, "_selection_timer", None)

        for _ in range(5):
            sync.enqueue_sync_after_quiet_period(delay_seconds=0.2)

        assert fired.wait(timeout=2)
        # Give any wrongly-surviving timers time to fire too.
        threading.Event().wait(0.4)
        assert calls == [1]


class TestStartPeriodicSync:
    def test_zero_interval_starts_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        started: List[object] = []
        monkeypatch.setattr(sync.threading, "Thread", lambda *a, **k: started.append(k))

        sync.start_periodic_sync(interval_hours=0)

        assert started == []
