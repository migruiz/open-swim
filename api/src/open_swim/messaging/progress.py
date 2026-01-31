from __future__ import annotations

import json
from typing import Optional, Protocol

from open_swim.messaging.models import SyncProgressMessage
from open_swim.messaging.mqtt import MqttClient


class ProgressReporter(Protocol):
    def report_progress(self, message: SyncProgressMessage) -> None:
        ...


class NullProgressReporter:
    def report_progress(self, message: SyncProgressMessage) -> None:
        return


class MqttProgressReporter:
    def __init__(self, mqtt_client: MqttClient) -> None:
        self._mqtt_client = mqtt_client

    def report_progress(self, message: SyncProgressMessage) -> None:
        try:
            payload = message.model_dump_json()
            self._mqtt_client.publish("openswim/sync/progress", payload, qos=0, retain=False)
        except Exception as exc:  # pragma: no cover - best effort only
            print(f"[MQTT] Failed to publish progress: {exc}")

        try:
            stages_summary = [
                {"name": s.name, "status": s.status.value, "error": s.error}
                for s in message.stages
            ]
            print(f"[PROGRESS] {json.dumps(stages_summary)}")
        except Exception:
            print("[PROGRESS] (failed to format progress message)")


_progress_reporter: Optional[ProgressReporter] = None


def set_progress_reporter(reporter: Optional[ProgressReporter]) -> None:
    global _progress_reporter
    _progress_reporter = reporter


def get_progress_reporter() -> ProgressReporter:
    if _progress_reporter is None:
        return NullProgressReporter()
    return _progress_reporter
