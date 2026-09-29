import json
from typing import Any, List, Tuple

import pytest

from open_swim import app


class FakeMqtt:
    def __init__(self) -> None:
        self.client = object()
        self.published: List[Tuple[str, str, bool]] = []
        self.subscribed: List[str] = []

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> Any:
        self.published.append((topic, payload, retain))

    def subscribe(self, topic: str, qos: int = 0) -> None:
        self.subscribed.append(topic)


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeMqtt:
    client = FakeMqtt()
    monkeypatch.setattr(app, "_mqtt_client", client)
    monkeypatch.setattr(app, "enqueue_sync", lambda: None)
    monkeypatch.setattr(app, "_last_device_status", ("disconnected", None, None))
    return client


def _status(client: FakeMqtt) -> dict[str, Any]:
    topic, payload, retain = client.published[-1]
    assert topic == "openswim/device/status" and retain
    return dict(json.loads(payload))


def test_connect_replaces_stale_status_with_disconnected(fake: FakeMqtt) -> None:
    app._on_mqtt_connected(fake)  # type: ignore[arg-type]

    assert _status(fake)["status"] == "disconnected"


def test_connect_republishes_the_last_known_status(fake: FakeMqtt) -> None:
    app._publish_device_status(status="safe_to_unplug", device="/dev/sda1")
    fake.published.clear()

    app._on_mqtt_connected(fake)  # type: ignore[arg-type]

    status = _status(fake)
    assert status["status"] == "safe_to_unplug"
    assert status["device"] == "/dev/sda1"


def test_sync_request_queues_a_sync(fake: FakeMqtt, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: List[int] = []
    monkeypatch.setattr(app, "enqueue_sync", lambda: calls.append(1))

    app._on_mqtt_message(fake, "openswim/sync/request", "")  # type: ignore[arg-type]

    assert calls == [1]


def test_connect_subscribes_to_sync_requests(fake: FakeMqtt) -> None:
    app._on_mqtt_connected(fake)  # type: ignore[arg-type]

    assert "openswim/sync/request" in fake.subscribed
