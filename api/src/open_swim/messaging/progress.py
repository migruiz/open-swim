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
        if message.percentage is None:
            if message.current_index is not None and message.total_count:
                try:
                    message.percentage = (message.current_index / message.total_count) * 100.0
                except Exception:
                    message.percentage = None

        try:
            payload = message.model_dump_json()
            self._mqtt_client.publish("openswim/sync/progress", payload, qos=0, retain=False)
        except Exception as exc:  # pragma: no cover - best effort only
            print(f"[MQTT] Failed to publish progress: {exc}")

        try:
            summary = json.dumps(
                {
                    "phase": message.phase,
                    "status": message.status,
                    "playlist_id": message.playlist_id,
                    "item_id": message.item_id,
                    "current_index": message.current_index,
                    "total_count": message.total_count,
                    "percentage": message.percentage,
                    "error_message": message.error_message,
                },
                default=str,
            )
            print(f"[PROGRESS] {summary}")
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
